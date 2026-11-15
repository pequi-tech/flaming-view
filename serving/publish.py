"""Padroniza, valida e publica os dados do pipeline (infra/) para o back-end.

  python publish.py ../infra/data release [--partial-year 2026]

Gera release/{versão}/ com grid/year=AAAA.parquet, factors.parquet, metrics.json e manifest.json
(+ predictions, territory, areas, model_metrics.json e areas/*.geojson se infra/data/model existir),
e só então aponta release/CURRENT para a nova versão. Qualquer violação do contract.json aborta
antes disso: o back-end nunca vê uma release pela metade ou fora do contrato.
"""
import datetime as dt, glob, hashlib, json, os, shutil, sys
import numpy as np
import pandas as pd
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = json.loads(Path(os.path.join(HERE, 'contract.json')).read_text())
GRID, FACTORS = CONTRACT['datasets']['grid'], CONTRACT['datasets']['factors']
MODEL = {k: CONTRACT['datasets'][k] for k in ('predictions', 'territory', 'areas')}
PARTIAL_COVERAGE = {2026: 'Brazil'}           # RD-01: 2026 só para o Brasil
GATES = CONTRACT['quality_gates']
ANTARCTICA = -60.0
ARCTIC = 75.0


class ContractError(Exception):
    pass


def source_for(year):
    return 'AQUA' if year <= 2011 else 'SNPP' if year <= 2025 else 'N20'


def cell_id(lat, lon):
    return ((np.round(lat * 20) + 1800) * 7200 + (np.round(lon * 20) + 3600)).astype('int32')


def cast(df, spec):
    """Colunas na ordem e nos tipos do contrato. Coluna faltando ou sobrando = erro."""
    cols = spec['columns']
    missing, extra = set(cols) - set(df), set(df) - set(cols)
    if missing or extra:
        raise ContractError(f'colunas: faltando {sorted(missing)}, sobrando {sorted(extra)}')
    out = {}
    for c, s in cols.items():
        x = df[c]
        if not s['nullable'] and x.isna().any():
            raise ContractError(f'{c}: {int(x.isna().sum())} nulos')
        if 'enum' in s and not x.dropna().isin(s['enum']).all():
            raise ContractError(f'{c}: fora do enum {sorted(set(x.dropna().astype(str)) - set(s["enum"]))[:5]}')
        out[c] = pd.Categorical(x, categories=s['enum']) if s['dtype'] == 'category' else x.astype(s['dtype'])
    return pd.DataFrame(out)


def standardize_grid(g):
    """Saída do infra -> formato do contrato. Devolve (df, relatório do que foi descartado/sinalizado)."""
    g = g.rename(columns={'lat05': 'lat', 'lon05': 'lon', 'raw': 'detections', 'cd01': 'cell_days', 'level': 'factor_level',
                          'viirs_eq': 'activity', 'lo': 'activity_lo', 'hi': 'activity_hi'})
    g = g.assign(lat=g.lat.round(2), lon=g.lon.round(2))
    ant = g.lat < ANTARCTICA
    report = {'dropped_antarctica_rows': int(ant.sum()), 'arctic_rows_kept': int((g.lat >= ARCTIC).sum())}
    g = g[~ant]
    g = g.assign(cell_id=cell_id(g.lat, g.lon))
    g = cast(g, GRID).sort_values(GRID['sort'], kind='stable').reset_index(drop=True)
    return g, report


def standardize_factors(f):
    f = f.assign(lat=f.lat.where(f.level != 'global'), lon=f.lon.where(f.level.isin(['c2', 'c10'])))
    return cast(f, FACTORS).sort_values(FACTORS['sort'], kind='stable').reset_index(drop=True)


def check_columns(df, spec):
    """Regras genéricas do contrato: tipo, nulos, enum, min/max."""
    errs = []
    for c, s in spec['columns'].items():
        x = df[c]
        want = 'category' if s['dtype'] == 'category' else s['dtype']
        if str(x.dtype) != want:
            errs.append(f'{c}: dtype {x.dtype} != {want}')
            continue
        if not s['nullable'] and x.isna().any():
            errs.append(f'{c}: {int(x.isna().sum())} nulos')
        v = x.dropna()
        if 'enum' in s and not v.isin(s['enum']).all():
            errs.append(f'{c}: fora do enum {sorted(set(v.astype(str)) - set(s["enum"]))[:5]}')
        if v.dtype.kind == 'f' and not np.isfinite(v).all():
            errs.append(f'{c}: valores infinitos')
        if 'min' in s and len(v) and ((v <= s['min']) if s.get('exclusive_min') else (v < s['min'])).any():
            errs.append(f'{c}: abaixo do mínimo {s["min"]} (ex.: {v.min()})')
        if 'max' in s and len(v) and (v > s['max']).any():
            errs.append(f'{c}: acima do máximo {s["max"]} (ex.: {v.max()})')
    if df.duplicated(spec['unique']).any():
        errs.append(f'chave {spec["unique"]} duplicada em {int(df.duplicated(spec["unique"]).sum())} linhas')
    return errs


def check_grid(g, year):
    """Regras do contrato + regras entre colunas que nenhum tipo garante."""
    errs = check_columns(g, GRID)
    if errs:
        return errs                                      # tipos errados invalidam as regras abaixo
    on_grid = lambda x: (np.abs(x * 20 - np.round(x * 20)) < 1e-6).all()
    rules = {
        'lat/lon fora da grade de 0,05°': not (on_grid(g.lat) and on_grid(g.lon)),
        'cell_id inconsistente com lat/lon': not (g.cell_id == cell_id(g.lat, g.lon)).all(),
        f'year diferente da partição {year}': not (g.year == year).all(),
        f'source diferente de {source_for(year)}': not (g.source == source_for(year)).all(),
        'cell_days > detections': (g.cell_days > g.detections).any(),
        'observed sem ser SNPP (ou SNPP convertido)': ((g.factor_level == 'observed') != (g.source == 'SNPP')).any(),
        'SNPP com factor != 1': (g.source == 'SNPP').any() and not np.allclose(g.factor[g.source == 'SNPP'], 1),
        'activity != cell_days / factor': not np.allclose(g.activity, g.cell_days / g.factor.astype('float64'), rtol=1e-4),
        'faixa de incerteza invertida': ((g.activity_lo > g.activity * (1 + 1e-6)) | (g.activity_hi < g.activity * (1 - 1e-6))).any(),
        'observado com faixa de incerteza': ((g.source == 'SNPP') & ~np.isclose(g.activity_lo, g.activity_hi)).any(),
        'fora da ordem do contrato (cell_id, month)': not (g.cell_id.astype('int64') * 100 + g.month).is_monotonic_increasing,
    }
    errs += [k for k, bad in rules.items() if bad]
    if year < dt.date.today().year and g.month.nunique() != GATES['months_per_complete_year']:
        errs.append(f'ano completo com {g.month.nunique()} meses')
    return errs


def check_metrics(m):
    errs = []
    if m['mape_total_monthly_pct'] > GATES['mape_total_monthly_pct_max']:
        errs.append(f"MAPE {m['mape_total_monthly_pct']} > {GATES['mape_total_monthly_pct_max']}")
    if m['r2_cell2_month'] < GATES['r2_cell2_month_min']:
        errs.append(f"R² {m['r2_cell2_month']} < {GATES['r2_cell2_month_min']}")
    if m['level_share'].get('c2', 0) < GATES['c2_level_share_min']:
        errs.append(f"fator próprio em só {m['level_share'].get('c2', 0):.0%} das células")
    return errs


def check_series(totals):
    """Salto de atividade global entre anos seguidos = sinal de troca de sensor mal harmonizada."""
    y = pd.Series(totals).sort_index()
    r = (y / y.shift()).dropna()
    lim = GATES['max_year_over_year_activity_ratio']
    return [f'atividade {a}->{b} mudou {v:.1f}x' for (a, b), v in zip(zip(r.index - 1, r.index), r) if v > lim or v < 1 / lim]


def standardize_model(name, df):
    if name in ('territory', 'predictions'):          # mesma regra do grid: Antártida fora
        df = df[df.cell_id >= int(cell_id(np.array([ANTARCTICA]), np.array([-180.0]))[0])]
    if name == 'areas':
        df = df.assign(w=df.bbox.str[0], s=df.bbox.str[1], e=df.bbox.str[2], n=df.bbox.str[3]).drop(columns=['bbox', 'centroid'])
    return cast(df, MODEL[name]).sort_values(MODEL[name]['sort'], kind='stable').reset_index(drop=True)


def publish_model(model_dir, tmp):
    """Previsão, território e áreas (contrato 1.1). Devolve erros; nada se o modelo não foi gerado."""
    if not os.path.isdir(model_dir):
        return []
    errs, frames = [], {}
    for name, spec in MODEL.items():
        df = standardize_model(name, pd.read_parquet(os.path.join(model_dir, spec['path'])))
        errs += [f'{name}: {e}' for e in check_columns(df, spec)]
        df.to_parquet(os.path.join(tmp, spec['path']), index=False, row_group_size=200_000)
        frames[name] = df
    p, t = frames['predictions'], frames['territory']
    if not np.isin(p.cell_id.to_numpy(), t.cell_id.to_numpy()).all():
        errs.append('predictions: cell_id sem território')
    if p.groupby('horizon').cell_id.nunique().nunique() != 1:
        errs.append('predictions: horizontes com conjuntos de células diferentes')
    shutil.copy(os.path.join(model_dir, 'metrics.json'), os.path.join(tmp, 'model_metrics.json'))
    shutil.copytree(os.path.join(model_dir, 'areas'), os.path.join(tmp, 'areas'))
    return errs


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def publish(infra_data, release_dir, version=None, partial_years=()):
    version = version or dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    tmp = os.path.join(release_dir, f'.{version}.tmp')
    final = os.path.join(release_dir, version)
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.join(tmp, 'grid'))
    try:
        metrics = json.loads(Path(os.path.join(infra_data, 'metrics.json')).read_text())
        errs = [f'metrics: {e}' for e in check_metrics(metrics)]
        quality, totals, files = {}, {}, {}
        for p in sorted(glob.glob(os.path.join(infra_data, 'grid', '*.parquet'))):
            year = int(os.path.basename(p)[:4])
            g, rep = standardize_grid(pd.read_parquet(p))
            errs += [f'grid {year}: {e}' for e in check_grid(g, year)]
            g.to_parquet(os.path.join(tmp, 'grid', f'year={year}.parquet'), index=False, row_group_size=200_000)
            totals[year] = float(g.activity.sum())
            quality[year] = {**rep, 'rows': len(g), 'cells': int(g.cell_id.nunique()), 'activity_total': round(totals[year], 1),
                             'months': sorted(int(m) for m in g.month.unique())}
        if not totals:
            errs.append('nenhum grid/*.parquet em ' + infra_data)
        errs += [f'série: {e}' for e in check_series({y: v for y, v in totals.items() if y not in partial_years})]
        errs += publish_model(os.path.join(infra_data, 'model'), tmp)
        f = standardize_factors(pd.read_csv(os.path.join(infra_data, 'factors.csv')))
        errs += [f'factors: {e}' for e in check_columns(f, FACTORS)]
        f.to_parquet(os.path.join(tmp, 'factors.parquet'), index=False)
        if errs:
            raise ContractError('release rejeitada:\n  ' + '\n  '.join(errs))
        Path(os.path.join(tmp, 'metrics.json')).write_text(json.dumps(metrics, indent=1))
        for p in sorted(glob.glob(os.path.join(tmp, '**', '*.*'), recursive=True)):
            rel = os.path.relpath(p, tmp)
            files[rel] = {'bytes': os.path.getsize(p), 'sha256': sha256(p)}
        manifest = {
            'version': version, 'contract_version': CONTRACT['version'],
            'created_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
            'years': [min(totals), max(totals)], 'rows': sum(q['rows'] for q in quality.values()),
            'partial_years': {str(y): {'coverage': PARTIAL_COVERAGE.get(y, 'unknown'), 'months': quality[y]['months']}
                              for y in partial_years if y in quality},
            'quality': {'per_year': quality, 'metrics': {k: metrics[k] for k in ('mape_total_monthly_pct', 'r2_cell2_month', 'level_share')}},
            'files': files,
        }
        Path(os.path.join(tmp, 'manifest.json')).write_text(json.dumps(manifest, indent=1))
        os.replace(tmp, final)                                    # release aparece inteira ou não aparece
        with open(os.path.join(release_dir, 'CURRENT.tmp'), 'w') as fh:
            fh.write(version + '\n')
        os.replace(os.path.join(release_dir, 'CURRENT.tmp'), os.path.join(release_dir, 'CURRENT'))
        return final, manifest
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def verify(release_path):
    """Confere uma release publicada: checksums do manifest e contrato. Para CI e para o back-end no boot."""
    m = json.loads(Path(os.path.join(release_path, 'manifest.json')).read_text())
    errs = [f'{rel}: checksum' for rel, info in m['files'].items() if sha256(os.path.join(release_path, rel)) != info['sha256']]
    if m['contract_version'].split('.')[0] != CONTRACT['version'].split('.')[0]:
        errs.append(f"contrato {m['contract_version']} incompatível com {CONTRACT['version']}")
    return errs


if __name__ == '__main__':
    if sys.argv[1:2] == ['verify']:
        e = verify(sys.argv[2]); print('\n'.join(e) or 'ok'); sys.exit(bool(e))
    try:
        args = sys.argv[1:]
        partial = [int(args[args.index('--partial-year') + 1])] if '--partial-year' in args else []
        path, man = publish(args[0], args[1], partial_years=partial)
    except ContractError as e:
        sys.exit(str(e))
    print(path, man['rows'], 'linhas', man['years'])
