"""Baixa os focos do FIRMS e já agrega: um arquivo pequeno por sensor × ano, sem guardar CSV bruto.

  python fetch.py --years 2003-2025                    # mundo inteiro (~10 GB de download, ~1 h)
  python fetch.py --country Brazil,Chile --years 2020-2025

Saída: data/agg/{sensor}_{ano}[_{países}].csv.gz  (ver aggregate.py). Retomável: pula o que já existe.
Fonte: https://firms.modaps.eosdis.nasa.gov/data/country/zips/{sensor}_{ano}_all_countries.zip
"""
import argparse, io, os, sys, zipfile, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import aggregate as ag

BASE = 'https://firms.modaps.eosdis.nasa.gov/data/country/zips'
SENSORS = {'modis': 2001, 'viirs-snpp': 2012, 'viirs-jpss1': 2018}   # sensor -> primeiro ano com arquivo
UA = {'User-Agent': 'Mozilla/5.0'}


def _get(req, tries=6, timeout=180):
    for i in range(tries):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError:
            raise                                     # 404 = ano sem arquivo; não insistir
        except Exception as e:                        # rede do FIRMS cai com frequência; insistir é o normal
            if i == tries - 1:
                raise
            print('retry', i + 1, e, file=sys.stderr)


class HttpFile(io.RawIOBase):
    """Arquivo remoto legível por seek/read usando HTTP Range: zipfile lê só o índice e os membros pedidos."""

    def __init__(self, url):
        self.url, self.pos = url, 0
        self.size = int(_get(urllib.request.Request(url, method='HEAD', headers=UA), timeout=120).headers['Content-Length'])

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def read(self, n=-1):
        if n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b''
        end = min(self.pos + n, self.size) - 1
        data = _get(urllib.request.Request(self.url, headers={**UA, 'Range': f'bytes={self.pos}-{end}'})).read()
        self.pos += len(data)
        return data

    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)


def _download(url, dst):
    """Download completo (≈9× mais rápido que Range no servidor do FIRMS)."""
    tmp = dst + '.part'
    with _get(urllib.request.Request(url, headers=UA), timeout=600) as r, open(tmp, 'wb') as f:
        while chunk := r.read(1 << 22):
            f.write(chunk)
    os.replace(tmp, dst)


def ingest(sensor, year, countries, out, tmp_dir):
    """Um zip anual -> um agregado. countries=None: mundo inteiro (baixa o zip todo); senão só esses países (Range)."""
    tag = '' if countries is None else '_' + '-'.join(countries)
    dst = os.path.join(out, f'{sensor}_{year}{tag}.csv.gz')
    if os.path.exists(dst):
        return dst, 'ok (já existia)'
    url = f'{BASE}/{sensor}_{year}_all_countries.zip'
    zpath = None
    try:
        if countries is None:
            zpath = os.path.join(tmp_dir, f'{sensor}_{year}.zip')
            _download(url, zpath)
            z = zipfile.ZipFile(zpath)
        else:
            z = zipfile.ZipFile(io.BufferedReader(HttpFile(url), buffer_size=1 << 20))
    except urllib.error.HTTPError as e:
        return dst, f'sem arquivo ({e.code})'
    members = [i for i in z.infolist() if i.filename.endswith('.csv')
               and (countries is None or any(i.filename.endswith(f'_{c}.csv') for c in countries))]
    if not members:
        return dst, 'nenhum país encontrado no zip'
    # ponytail: agrega país a país (memória baixa); um foco na fronteira entre dois CSVs de país pode contar 2× em cd01.
    # Efeito desprezível (células de 1 km na divisa); juntar membros antes do cell_days se algum dia importar.
    parts = [ag.aggregate_file(z.open(m)) for m in members]
    a = pd.concat(parts).groupby(ag.KEYS, as_index=False)[['raw', 'cd01']].sum()
    a.to_csv(dst + '.part', index=False, compression='gzip')
    os.replace(dst + '.part', dst)                     # só aparece completo
    if zpath:
        os.remove(zpath)
    return dst, f'ok {len(members)} países, {len(a)} linhas'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--country', default='ALL', help='ALL ou lista separada por vírgula, nomes como no FIRMS (Brazil, United_States)')
    p.add_argument('--years', default='2003-2025')
    p.add_argument('--out', default='data/agg')
    p.add_argument('--jobs', type=int, default=4)
    a = p.parse_args()
    y0, y1 = map(int, a.years.split('-'))
    countries = None if a.country.upper() == 'ALL' else a.country.split(',')
    tmp_dir = os.path.join(a.out, '..', 'tmp')
    os.makedirs(a.out, exist_ok=True); os.makedirs(tmp_dir, exist_ok=True)
    jobs = [(s, y) for s, first in SENSORS.items() for y in range(max(y0, first), y1 + 1)]
    with ThreadPoolExecutor(a.jobs) as ex:
        for dst, msg in ex.map(lambda j: ingest(*j, countries, a.out, tmp_dir), jobs):
            print(os.path.basename(dst), msg, flush=True)


if __name__ == '__main__':
    main()
