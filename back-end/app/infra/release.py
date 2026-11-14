"""Release publicada pelo serving/: DuckDB direto nos Parquet do manifest."""
import hashlib, json
from pathlib import Path
import duckdb

from ..domain.area import BBox

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
