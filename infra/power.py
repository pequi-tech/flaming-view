"""NASA POWER mensal (RD-03): chuva, temperatura, umidade e vento, 2003→hoje, América do Sul.

  python power.py [--out data/ext/power_05.parquet]

A API regional aceita 1 parâmetro por chamada e caixas de até 10°; a grade é 0,5° (lat) × 0,625° (lon).
Saída: lat, lon (ponto POWER), year, month, prec (mm/dia), t2m (°C), rh2m (%), ws2m (m/s). Mês sem dado = NaN.
"""
import argparse, io, json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd

API = 'https://power.larc.nasa.gov/api/temporal/monthly/regional'
PARAMS = {'PRECTOTCORR': 'prec', 'T2M': 't2m', 'RH2M': 'rh2m', 'WS2M': 'ws2m'}
SOUTH_AMERICA = (-82, -56, -34, 13)        # W, S, E, N; o resto do mundo fica sem POWER (declarado no /method)
TILE = 10


def get(param, w, s, e, n, y0, y1, tries=5):
    url = (f'{API}?parameters={param}&community=AG&longitude-min={w}&longitude-max={e}'
           f'&latitude-min={s}&latitude-max={n}&start={y0}&end={y1}&format=JSON')
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'flaming-view'}), timeout=300) as r:
                d = json.load(r)
            if 'features' not in d:
                raise RuntimeError(d.get('messages'))
            rows = []
            for f in d['features']:
                lon, lat = f['geometry']['coordinates'][:2]
                for k, v in f['properties']['parameter'][param].items():
                    if k[4:] != '13':                              # 13 = média anual
                        rows.append((round(lat, 3), round(lon, 3), int(k[:4]), int(k[4:]), np.nan if v <= -999 else v))
            return pd.DataFrame(rows, columns=['lat', 'lon', 'year', 'month', PARAMS[param]])
        except Exception as ex:
            if i == tries - 1:
                raise
            print('retry', param, w, s, ex, file=sys.stderr, flush=True)
            time.sleep(5 * (i + 1))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', default='data/ext/power_05.parquet')
    p.add_argument('--years', default=f'2003-{pd.Timestamp.now().year}')
    a = p.parse_args()
    y0, y1 = map(int, a.years.split('-'))
    W, S, E, N = SOUTH_AMERICA
    tiles = [(x, y, min(x + TILE, E), min(y + TILE, N)) for x in range(W, E, TILE) for y in range(S, N, TILE)]
    jobs = [(param, *t) for param in PARAMS for t in tiles]
    with ThreadPoolExecutor(4) as ex:
        parts = list(ex.map(lambda j: get(*j, y0, y1), jobs))
    frames = {}
    for (param, *_), df in zip(jobs, parts):
        frames.setdefault(PARAMS[param], []).append(df)
    keys = ['lat', 'lon', 'year', 'month']
    out = None
    for var, dfs in frames.items():
        d = pd.concat(dfs).drop_duplicates(keys)                  # caixas vizinhas repetem a borda
        out = d if out is None else out.merge(d, on=keys, how='outer')
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    out.sort_values(keys).to_parquet(a.out, index=False)
    print(a.out, len(out), 'linhas', out[['lat', 'lon']].drop_duplicates().shape[0], 'pontos',
          f"{out.year.min()}-{out.year.max()}", 'último mês com chuva:',
          out.dropna(subset=['prec']).eval('year*100+month').max(), flush=True)


if __name__ == '__main__':
    main()
