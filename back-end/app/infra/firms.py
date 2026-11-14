"""FIRMS em tempo real: API de área, janelas de 5 dias em paralelo, cache SQLite."""
import datetime as dt, io, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd

from ..domain.area import BBox
from ..domain.errors import RealtimeUnavailable
from .cache import Cache

# Mesmos filtros e mesma contagem de células-dia do pipeline: NRT e arquivo nunca divergem.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'infra'))
import aggregate  # noqa: E402


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

    CLOSED_TTL = 7 * 86400                            # dias com mais de 2 dias já não mudam no NRT

    def _window(self, area, start, days, ttl):
        """CSV de uma janela. Devolve (texto, veio_de_snapshot_vencido)."""
        path = f'{self.SOURCE}/{area}/{days}/{start.isoformat()}'
        hit = self.cache.get(path)                    # chave sem a MAP_KEY
        if hit and time.time() - hit[1] < ttl:
            return hit[0], False
        try:
            text = self.fetch(f'{self.BASE}/{self.key}/{path}')
            if not text.startswith('latitude'):
                raise RealtimeUnavailable(text[:200])    # o FIRMS responde erros como texto com status 200
        except Exception as e:
            if hit:
                return hit[0], True
            raise RealtimeUnavailable(str(e)) from e
        self.cache.put(path, text)
        return text, False

    def cell_days(self, bbox: BBox, first, last):
        """Células-dia (mesma regra do pipeline) entre first e last, dentro da caixa. Devolve (total, algum_snapshot_vencido)."""
        if not self.key:
            raise RealtimeUnavailable('FIRMS_MAP_KEY não configurada')
        windows = []
        for w, e in bbox.lon_ranges():
            area = f'{w:g},{bbox.s:g},{e:g},{bbox.n:g}'
            day = first
            while day <= last:
                days = min(self.MAX_DAYS, (last - day).days + 1)
                end = day + dt.timedelta(days=days - 1)
                windows.append((area, day, days, self.CLOSED_TTL if (last - end).days > 2 else self.ttl))
                day = end + dt.timedelta(days=1)
        with ThreadPoolExecutor(min(8, len(windows))) as ex:      # janelas em paralelo: 1ª chamada = janela mais lenta
            results = list(ex.map(lambda a: self._window(*a), windows))
        stale = any(s for _, s in results)
        frames = [pd.read_csv(io.StringIO(t)) for t, _ in results]
        d = pd.concat(frames)
        if d.empty:
            return 0, stale
        d = d.assign(type=0)                          # ponytail: NRT não traz `type`; fontes estáticas (gás, indústria) entram. Máscara de fontes estáticas do FIRMS se incomodar.
        c = aggregate.clean(d)
        return int(aggregate.cell_days(c).cd01.sum()) if len(c) else 0, stale
