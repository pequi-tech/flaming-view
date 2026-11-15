"""2026 só para o Brasil, pela API de área do FIRMS (NOAA-20), em janelas de 10 dias.

  FIRMS_MAP_KEY=... python fetch_2026.py [--until 2026-10-31] [--out data/agg]

Usa VIIRS_NOAA20_SP até onde o arquivo científico existe e VIIRS_NOAA20_NRT depois disso.
Saída: data/agg/viirs-jpss1_2026_Brazil.csv.gz (mesmo formato do fetch.py); o harmonize.py
já pega o arquivo (`{sensor}_{ano}_*.csv.gz`) e converte N20 -> S-NPP.
"""
import argparse, datetime as dt, io, os, sys
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import aggregate as ag
from fetch import _get, UA
import urllib.request

API = 'https://firms.modaps.eosdis.nasa.gov/api'
BRAZIL = '-74,-34,-34,6'
DAYS = 5                      # a API de área aceita até 5 dias por chamada


def get_text(url):
    with _get(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return r.read().decode()


def sp_end(key):
    """Último dia do arquivo científico (SP) do NOAA-20."""
    d = pd.read_csv(io.StringIO(get_text(f'{API}/data_availability/csv/{key}/VIIRS_NOAA20_SP')))
    return dt.date.fromisoformat(str(d.max_date.iloc[0]))


def window(key, src, start, days):
    text = get_text(f'{API}/area/csv/{key}/{src}/{BRAZIL}/{days}/{start.isoformat()}')
    if not text.startswith('latitude'):
        raise RuntimeError(f'{src} {start}: {text[:200]}')   # FIRMS devolve erro como texto com status 200
    d = pd.read_csv(io.StringIO(text))
    if d.empty:
        return None
    d = d.assign(satellite='N20', type=d['type'] if 'type' in d else 0)   # NRT não traz `type`
    return ag.cell_days(ag.clean(d))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--until', default=None, help='último dia (padrão: último dia do mês anterior)')
    p.add_argument('--out', default='data/agg')
    a = p.parse_args()
    key = os.environ.get('FIRMS_MAP_KEY') or sys.exit('defina FIRMS_MAP_KEY')
    today = dt.date.today()
    until = dt.date.fromisoformat(a.until) if a.until else today.replace(day=1) - dt.timedelta(days=1)
    end_sp = sp_end(key)
    jobs, day = [], dt.date(2026, 1, 1)
    while day <= until:
        days = min(DAYS, (until - day).days + 1)
        jobs.append(('VIIRS_NOAA20_SP' if day + dt.timedelta(days=days - 1) <= end_sp else 'VIIRS_NOAA20_NRT', day, days))
        day += dt.timedelta(days=days)
    print(f'SP até {end_sp}; {len(jobs)} janelas até {until}', flush=True)
    with ThreadPoolExecutor(4) as ex:
        parts = [x for x in ex.map(lambda j: window(key, *j), jobs) if x is not None]
    # janelas não se sobrepõem em dias, então somar por célula-mês é exato
    agg = pd.concat(parts).groupby(ag.KEYS, as_index=False)[['raw', 'cd01']].sum()
    agg = agg[agg.year == 2026]
    dst = os.path.join(a.out, 'viirs-jpss1_2026_Brazil.csv.gz')
    agg.to_csv(dst + '.part', index=False, compression='gzip')
    os.replace(dst + '.part', dst)
    print(dst, len(agg), 'linhas', sorted(agg.month.unique()), flush=True)


if __name__ == '__main__':
    main()
