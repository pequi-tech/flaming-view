"""Filtros e contagem de células-dia (usados pelo fetch.py e pelo back-end no tempo real).

Mesmos filtros para lote (SP) e tempo real (NRT): só vegetação (type=0) e confiança >= nominal.
Duas métricas por célula 0,05° × mês × sensor × dia/noite:
  raw  = detecções;  cd01 = células-dia de 0,01° (~1 km), a unidade estável entre sensores.

Converter CSVs já baixados (ex.: arquivos por país) para o formato de data/agg:
  python aggregate.py data/raw data/agg
"""
import glob, os, sys
import numpy as np
import pandas as pd

COLS = ['latitude', 'longitude', 'acq_date', 'satellite', 'confidence', 'daynight', 'type']
SRC = {'Aqua': 'AQUA', 'A': 'AQUA', 'Terra': 'TERRA', 'T': 'TERRA', 'N': 'SNPP', 'N20': 'N20', '1': 'N20', 'N21': 'N21'}
KEYS = ['src', 'daynight', 'year', 'month', 'lat05', 'lon05']


def clean(d):
    """Filtra e normaliza o sensor. MODIS: confiança 0-100 (>=30). VIIRS: l/n/h ou low/nominal/high."""
    d = d[d['type'] == 0]
    conf = d.confidence.astype(str).str.lower()
    ok = conf.isin(['n', 'h', 'nominal', 'high']) | pd.to_numeric(conf, errors='coerce').ge(30)
    d = d[ok]
    return d.assign(src=d.satellite.astype(str).map(SRC)).dropna(subset=['src'])


def cell_days(d):
    """Conta `raw` e `cd01` por célula 0,05° × mês × sensor × dia/noite."""
    t = pd.to_datetime(d.acq_date)
    # *100 e round antes do floor: 0.35/0.01 = 34.999... cairia na célula errada
    gy, gx = np.floor(np.round(d.latitude * 100, 6)).astype(int), np.floor(np.round(d.longitude * 100, 6)).astype(int)
    d = d.assign(year=t.dt.year, month=t.dt.month, gy=gy, gx=gx,
                 lat05=((gy // 5) * 0.05).round(2), lon05=((gx // 5) * 0.05).round(2))
    raw = d.groupby(KEYS).size().rename('raw')
    cd01 = d.drop_duplicates(['src', 'daynight', 'acq_date', 'gy', 'gx']).groupby(KEYS).size().rename('cd01')
    return pd.concat([raw, cd01], axis=1).reset_index()


def aggregate_file(path_or_buffer):
    return cell_days(clean(pd.read_csv(path_or_buffer, usecols=COLS)))


def main(raw_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(raw_dir, '*_*_*.csv'))):
        dst = os.path.join(out_dir, os.path.basename(f)[:-4] + '.csv.gz')
        if not os.path.exists(dst):
            aggregate_file(f).to_csv(dst, index=False, compression='gzip')
        print(os.path.basename(dst), flush=True)


if __name__ == '__main__':
    main(*sys.argv[1:3])
