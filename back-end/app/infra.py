"""Infraestrutura: release (DuckDB sobre Parquet), FIRMS tempo real e cache SQLite."""
import io, json, sqlite3, sys, threading, time, urllib.request
from contextlib import contextmanager
from pathlib import Path
import duckdb
import pandas as pd

from .domain import BBox

# Mesmos filtros e mesma contagem de células-dia do pipeline: NRT e arquivo nunca divergem.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'infra'))
import aggregate  # noqa: E402

CONTRACT_MAJOR = '1'


class Release:
    """Release publicada pelo serving/. Só sobe se o manifest bater com os arquivos e com o contrato."""

    def __init__(self, release_dir, verify_sha=False):
        root = Path(release_dir)
        self.version = (root / 'CURRENT').read_text().strip()
        self.path = root / self.version
        self.manifest = json.loads((self.path / 'manifest.json').read_text())
        self.metrics = json.loads((self.path / 'metrics.json').read_text())
        self._check(verify_sha)
        files = sorted(str(self.path / f) for f in self.manifest['files'] if f.startswith('grid/'))
        self.db = duckdb.connect()
        self.db.execute(f"CREATE VIEW grid AS SELECT * FROM read_parquet({files!r})")
        self.years = list(range(self.manifest['years'][0], self.manifest['years'][1] + 1))

    def _check(self, verify_sha):
        m = self.manifest
        if m['contract_version'].split('.')[0] != CONTRACT_MAJOR:
            raise RuntimeError(f"release {self.version}: contrato {m['contract_version']}, back-end espera {CONTRACT_MAJOR}.x")
        for rel, info in m['files'].items():
            p = self.path / rel
            if not p.exists() or p.stat().st_size != info['bytes']:
                raise RuntimeError(f'release {self.version}: {rel} ausente ou com tamanho diferente do manifest')
            if verify_sha and 'sha256' in info:
                import hashlib
                h = hashlib.sha256()
                with open(p, 'rb') as f:
                    for chunk in iter(lambda: f.read(1 << 20), b''):
                        h.update(chunk)
                if h.hexdigest() != info['sha256']:
                    raise RuntimeError(f'release {self.version}: {rel} corrompido')

    @staticmethod
    def _where(bbox: BBox | None):
        """Células de 0,05° que intersectam a caixa (intervalos abertos; antimeridiano = duas faixas)."""
        if bbox is None:
            return 'TRUE', []
        lat0, lat1 = bbox.lat_open_interval()
        lons = bbox.lon_ranges()
        sql = f"lat > ? AND lat < ? AND ({' OR '.join(['(lon > ? AND lon < ?)'] * len(lons))})"
        return sql, [lat0, lat1] + [v for w, e in lons for v in (w - 0.05, e)]

    def monthly(self, bbox: BBox):
        """{(ano, mês): soma} para valor, lo e hi, mais a fonte de cada ano."""
        where, params = self._where(bbox)
        rows = self.db.cursor().execute(
            f"SELECT year, month, sum(activity), sum(activity_lo), sum(activity_hi), any_value(source::VARCHAR) "
            f"FROM grid WHERE {where} GROUP BY ALL", params).fetchall()
        val = {(y, m): float(v) for y, m, v, _, _, _ in rows}
        lo = {(y, m): float(v) for y, m, _, v, _, _ in rows}
        hi = {(y, m): float(v) for y, m, _, _, v, _ in rows}
        return val, lo, hi, {y: s for y, _, _, _, _, s in rows}

    def cells(self, year, month, res, bbox: BBox | None):
        where, params = self._where(bbox)
        return self.db.cursor().execute(
            f"SELECT floor(lat / ?) * ? AS la, floor(lon / ?) * ? AS lo, sum(activity) FROM grid "
            f"WHERE year = ? AND month = ? AND {where} GROUP BY ALL ORDER BY la, lo",
            [res, res, res, res, year, month] + params).fetchall()


class Cache:
    """Chave-valor com validade em SQLite. Guarda o último valor mesmo vencido, para servir como snapshot se a fonte cair."""

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        with self._conn() as c:
            c.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, stored REAL NOT NULL)')

    @contextmanager
    def _conn(self):
        c = sqlite3.connect(self.path, timeout=10)   # `with sqlite3.connect()` só comita, não fecha
        try:
            with c:
                yield c
        finally:
            c.close()

    def get(self, key):
        """(valor, guardado_em) ou None."""
        with self._conn() as c:
            return c.execute('SELECT value, stored FROM cache WHERE key = ?', (key,)).fetchone()

    def put(self, key, value):
        with self.lock, self._conn() as c:
            c.execute('INSERT OR REPLACE INTO cache VALUES (?, ?, ?)', (key, value, time.time()))


class FirmsUnavailable(Exception):
    pass


def http_get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'flaming-view'}), timeout=30) as r:
        return r.read().decode()


class Firms:
    """API de área do FIRMS (tempo real). Cada janela de até 5 dias é cacheada no SQLite."""
    BASE = 'https://firms.modaps.eosdis.nasa.gov/api/area/csv'
    SOURCE = 'VIIRS_NOAA21_NRT'
    MAX_DAYS = 5

    def __init__(self, map_key, cache: Cache, fetch=http_get, ttl=3600):
        self.key, self.cache, self.fetch, self.ttl = map_key, cache, fetch, ttl

    def _window(self, area, start, days):
        """CSV de uma janela. Devolve (texto, veio_de_snapshot_vencido)."""
        path = f'{self.SOURCE}/{area}/{days}/{start.isoformat()}'
        hit = self.cache.get(path)                    # chave sem a MAP_KEY
        if hit and time.time() - hit[1] < self.ttl:
            return hit[0], False
        try:
            text = self.fetch(f'{self.BASE}/{self.key}/{path}')
            if not text.startswith('latitude'):
                raise FirmsUnavailable(text[:200])    # o FIRMS responde erros como texto com status 200
        except Exception as e:
            if hit:
                return hit[0], True
            raise FirmsUnavailable(str(e)) from e
        self.cache.put(path, text)
        return text, False

    def cell_days(self, bbox: BBox, first, last):
        """Células-dia (mesma regra do pipeline) entre first e last, dentro da caixa. Devolve (total, algum_snapshot_vencido)."""
        if not self.key:
            raise FirmsUnavailable('FIRMS_MAP_KEY não configurada')
        frames, stale = [], False
        for w, e in bbox.lon_ranges():
            area = f'{w:g},{bbox.s:g},{e:g},{bbox.n:g}'
            day = first
            while day <= last:
                days = min(self.MAX_DAYS, (last - day).days + 1)
                text, s = self._window(area, day, days)
                stale |= s
                frames.append(pd.read_csv(io.StringIO(text)))
                day += pd.Timedelta(days=days).to_pytimedelta()
        d = pd.concat(frames)
        if d.empty:
            return 0, stale
        d = d.assign(type=0)                          # ponytail: NRT não traz `type`; fontes estáticas (gás, indústria) entram. Máscara de fontes estáticas do FIRMS se incomodar.
        c = aggregate.clean(d)
        return int(aggregate.cell_days(c).cd01.sum()) if len(c) else 0, stale
