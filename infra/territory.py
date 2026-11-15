"""Território das células 0,05° (RD-07) e áreas administrativas (RD-09).

  python territory.py data ../front-end/public/data/countries.geojson

Entradas em data/ext/: br_mun.geojson, br_uf.geojson (IBGE malha mínima), mun_meta.json, pop2024.json (IBGE),
ti/*.geojson (terras indígenas FUNAI, via TerraBrasilis/INPE, um arquivo por bioma).
Saídas em data/model/: territory.parquet, areas.parquet, areas/{countries,states,municipalities}.geojson.

V = rank da atividade acumulada da célula (anos completos). E_pop = rank da densidade populacional: município
(IBGE 2024) no Brasil, país (Natural Earth) fora. E_ti = 1 se >= 20 % da célula (amostra 5×5) cai em TI.
E = max(E_pop, 0,8·E_ti). Tudo com piso 0,05. Com data/ext/ghsl.zip (GHSL POP 2025, 30″),
E_pop passa a ser o rank da população da própria célula e a coluna `pop` guarda as pessoas.
"""
import glob, json, math, os, shutil, sys, unicodedata
import numpy as np
import pandas as pd
import duckdb

FLOOR = 0.05
TI_SHARE = 0.20
MAX_RING = 4000               # ponytail: anéis longos (TIs da Amazônia) decimados; erro < 1 célula de 0,05°


def rings_of(geom):
    polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    out = []
    for poly in polys:
        for r in poly:
            r = np.asarray(r, float)
            out.append(r[::math.ceil(len(r) / MAX_RING)] if len(r) > MAX_RING else r)
    return out


def inside(px, py, rings):
    """Ponto-em-polígono par-ímpar sobre todos os anéis (buracos e partes inclusos)."""
    c = np.zeros(len(px), bool)
    for r in rings:
        x, y = r[:, 0], r[:, 1]
        x0, y0, x1, y1 = x[:-1], y[:-1], x[1:], y[1:]
        for i in range(len(x0)):
            yi, yj = y0[i], y1[i]
            if yi == yj:
                continue
            hit = (yi > py) != (yj > py)
            if hit.any():
                c[hit] ^= px[hit] < (x1[i] - x0[i]) * (py[hit] - yi) / (yj - yi) + x0[i]
    return c


def bbox(rings):
    a = np.vstack(rings)
    return a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max()


def assign(px, py, features, key):
    """Para cada ponto, o `key` do primeiro polígono que o contém (None se nenhum). Pré-filtro por caixa."""
    out = np.full(len(px), None, object)
    for f in features:
        rings = rings_of(f['geometry'])
        w, s, e, n = bbox(rings)
        cand = np.flatnonzero((px >= w) & (px <= e) & (py >= s) & (py <= n) & (out == None))  # noqa: E711
        if len(cand):
            hit = inside(px[cand], py[cand], rings)
            out[cand[hit]] = key(f)
    return out


def ghsl_population(zip_path, lat, lon):
    """População GHSL 2025 (30″ ≈ 1 km, WGS84) somada em cada célula de 0,05° (6 × 6 pixels). lat/lon = canto SW."""
    import tifffile, zipfile
    with zipfile.ZipFile(zip_path) as z:
        name = next(n for n in z.namelist() if n.endswith('.tif'))
        tmp = os.path.join(os.path.dirname(zip_path), name)
        z.extract(name, os.path.dirname(zip_path))
    try:
        with tifffile.TiffFile(tmp) as t:
            page = t.pages[0]
            sx = page.tags['ModelPixelScaleTag'].value[0]
            x0, y0 = page.tags['ModelTiepointTag'].value[3:5]          # canto NW do raster
            a = page.asarray()
    finally:
        os.remove(tmp)
    a = np.where(a > 0, a, 0).astype(np.float32)                         # nodata (-200) e negativos = 0
    k = int(round(0.05 / sx))                                            # pixels por célula (6)
    rows, cols = a.shape[0] // k, a.shape[1] // k
    g = a[:rows * k, :cols * k].reshape(rows, k, cols, k).sum((1, 3))
    del a
    r = np.floor((y0 - (lat + 0.05)) / 0.05 + 1e-6).astype(int)           # linha da célula a partir do topo
    c = np.floor((lon - x0) / 0.05 + 1e-6).astype(int)
    ok = (r >= 0) & (r < rows) & (c >= 0) & (c < cols)
    out = np.zeros(len(lat), np.float32)
    out[ok] = g[r[ok], c[ok]]
    return out


def apply_ghsl(out, zip_path):
    """E_pop = rank da população GHSL da própria célula (A9 do PRD), em vez da densidade do município."""
    t = pd.read_parquet(os.path.join(out, 'territory.parquet'))
    t['pop'] = ghsl_population(zip_path, t.lat.to_numpy(), t.lon.to_numpy())
    t['e_pop'] = rank(t['pop'])
    t['e'] = np.maximum(t.e_pop, np.float32(0.8) * t.e_ti).clip(FLOOR).astype('float32')
    t.to_parquet(os.path.join(out, 'territory.parquet'), index=False, row_group_size=200_000)
    print('GHSL: população total', round(float(t['pop'].sum()) / 1e9, 2), 'bi nas células com fogo;',
          'células com pop > 0:', int((t['pop'] > 0).sum()), flush=True)


def rank(x):
    return pd.Series(x).rank(pct=True).clip(lower=FLOOR).to_numpy(np.float32)


def area_km2(rings):
    a = 0.0
    for r in rings:
        k = math.cos(math.radians(r[:, 1].mean()))
        x, y = np.radians(r[:, 0]) * 6371 * k, np.radians(r[:, 1]) * 6371
        a += abs(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1])) / 2
    return a


def fold(s):
    return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().lower()


def main(data, countries_path):
    ext, out = os.path.join(data, 'ext'), os.path.join(data, 'model')
    os.makedirs(os.path.join(out, 'areas'), exist_ok=True)
    full = sorted(int(os.path.basename(p)[:4]) for p in glob.glob(os.path.join(data, 'grid', '*.parquet')) if int(os.path.basename(p)[:4]) <= 2025)
    cells = duckdb.sql(f"""
        SELECT (round(lat05 * 20) + 1800)::INT * 7200 + (round(lon05 * 20) + 3600)::INT AS cell_id,
               round(lat05, 2) AS lat, round(lon05, 2) AS lon, sum(viirs_eq) AS total
        FROM read_parquet('{data}/grid/*.parquet') WHERE year BETWEEN {full[0]} AND {full[-1]} GROUP BY ALL""").df()
    px, py = (cells.lon + 0.025).to_numpy(), (cells.lat + 0.025).to_numpy()
    print('células', len(cells), flush=True)

    meta = {str(m['id']): m for m in json.load(open(os.path.join(ext, 'mun_meta.json')))}
    pop = {s['localidade']['id']: int(s['serie']['2024']) if s['serie']['2024'].isdigit() else 0   # IBGE usa '...' para sem dado
           for s in json.load(open(os.path.join(ext, 'pop2024.json')))[0]['resultados'][0]['series']}
    mun = json.load(open(os.path.join(ext, 'br_mun.geojson')))['features']
    uf = json.load(open(os.path.join(ext, 'br_uf.geojson')))['features']
    countries = json.load(open(countries_path))['features']

    br = (px > -74.5) & (px < -28.5) & (py > -34.5) & (py < 5.5)
    mid = np.full(len(cells), None, object)
    mid[br] = assign(px[br], py[br], mun, lambda f: f['properties']['codarea'])
    print('municípios', int((mid != None).sum()), flush=True)  # noqa: E711
    country = assign(px, py, [f for f in countries], lambda f: f['properties']['ADM0_A3'])
    country[mid != None] = 'BRA'  # noqa: E711
    # célula de costa/fronteira que o Natural Earth põe no Brasil mas cujo centro cai fora da malha do IBGE: município mais próximo
    mun_c = {f['properties']['codarea']: np.vstack(rings_of(f['geometry'])).mean(0) for f in mun}
    lost = np.flatnonzero((country == 'BRA') & (mid == None))  # noqa: E711
    if len(lost):
        ids = np.array(list(mun_c)); xy = np.array(list(mun_c.values()))
        mid[lost] = ids[((xy[None, :, 0] - px[lost, None]) ** 2 + (xy[None, :, 1] - py[lost, None]) ** 2).argmin(1)]

    # exposição populacional: densidade do município (Brasil) ou do país (resto)
    mun_area = {f['properties']['codarea']: area_km2(rings_of(f['geometry'])) for f in mun}
    dens_mun = {k: pop.get(k, 0) / max(a, 1) for k, a in mun_area.items()}
    dens_cty = {f['properties']['ADM0_A3']: float(f['properties'].get('POP_EST') or 0) / max(area_km2(rings_of(f['geometry'])), 1)
                for f in countries}
    dens = np.array([dens_mun.get(m, 0) if m else dens_cty.get(c, 0) for m, c in zip(mid, country)], float)

    # terras indígenas: 25 pontos por célula do Brasil
    ti = [f for p in sorted(glob.glob(os.path.join(ext, 'ti', '*.geojson'))) for f in json.load(open(p))['features']]
    bi = np.flatnonzero(mid != None)  # noqa: E711
    off = (np.arange(5) + 0.5) * 0.01
    sx = (cells.lon.to_numpy()[bi, None, None] + off[None, None, :]).repeat(5, 1).ravel()
    sy = (cells.lat.to_numpy()[bi, None, None] + off[None, :, None]).repeat(5, 2).ravel()
    name = assign(sx, sy, ti, lambda f: f['properties']['terrai_nom']).reshape(len(bi), 25)
    share = (name != None).mean(1)  # noqa: E711
    ti_name = np.full(len(cells), None, object)
    e_ti = np.zeros(len(cells), np.float32)
    for j, i in enumerate(bi):
        if share[j] >= TI_SHARE:
            e_ti[i] = 1.0
            vals, cnt = np.unique(name[j][name[j] != None].astype(str), return_counts=True)  # noqa: E711
            ti_name[i] = vals[cnt.argmax()]
    print('células em TI', int(e_ti.sum()), flush=True)

    e_pop = rank(dens)
    t = pd.DataFrame({'cell_id': cells.cell_id.astype('int32'), 'lat': cells.lat, 'lon': cells.lon,
                      'v': rank(cells.total), 'e_pop': e_pop, 'e_ti': e_ti,
                      'e': np.maximum(e_pop, np.float32(0.8) * e_ti).clip(FLOOR).astype('float32'),
                      'ti_name': ti_name, 'municipality_id': mid,
                      'state_id': [m[:2] if m else None for m in mid], 'country': country})
    import h3
    for r in (4, 5, 6):
        t[f'h3_{r}'] = [h3.latlng_to_cell(la + 0.025, lo + 0.025, r) for la, lo in zip(t.lat, t.lon)]
    t.sort_values('cell_id').to_parquet(os.path.join(out, 'territory.parquet'), index=False, row_group_size=200_000)
    ghsl = os.path.join(ext, 'ghsl.zip')
    if os.path.exists(ghsl):
        apply_ghsl(out, ghsl)
    build_areas(out, meta, pop, mun, uf, countries, countries_path)


def build_areas(out, meta, pop, mun, uf, countries, countries_path):
    """Áreas: país -> estado -> município, mais os GeoJSON servidos por /areas/{id}/geometry."""
    rows = []
    for f in countries:
        p = f['properties']; w, s, e, n = bbox(rings_of(f['geometry']))
        rows.append((p['ADM0_A3'], 'country', p.get('NAME_PT') or p['NAME'], None, [w, s, e, n], [(w + e) / 2, (s + n) / 2]))
    ufs = {}
    for m in meta.values():                    # município novo pode vir sem microrregião no IBGE
        if m.get('microrregiao'):
            u = m['microrregiao']['mesorregiao']['UF']; ufs[str(u['id'])] = u
    for f in uf:
        c = f['properties']['codarea']; w, s, e, n = bbox(rings_of(f['geometry']))
        rows.append((f'BR{c}', 'state', ufs[c]['nome'], 'BRA', [w, s, e, n], [(w + e) / 2, (s + n) / 2]))
    for f in mun:
        c = f['properties']['codarea']; w, s, e, n = bbox(rings_of(f['geometry']))
        uf_ = ufs[c[:2]]
        rows.append((f'BR{c}', 'municipality', f"{meta[c]['nome']} - {uf_['sigla']}", f'BR{c[:2]}', [w, s, e, n], [(w + e) / 2, (s + n) / 2]))
    a = pd.DataFrame(rows, columns=['area_id', 'level', 'name', 'parent_id', 'bbox', 'centroid'])
    a['search'] = a.name.map(fold)
    a['population'] = [pop.get(i[2:], 0) if l == 'municipality' else None for i, l in zip(a.area_id, a.level)]
    a.to_parquet(os.path.join(out, 'areas.parquet'), index=False)
    for f in uf: f['properties'] = {'area_id': f"BR{f['properties']['codarea']}", 'name': ufs[f['properties']['codarea']]['nome']}
    for f in mun: f['properties'] = {'area_id': f"BR{f['properties']['codarea']}", 'name': meta[f['properties']['codarea']]['nome']}
    json.dump({'type': 'FeatureCollection', 'features': uf}, open(os.path.join(out, 'areas', 'states.geojson'), 'w'))
    json.dump({'type': 'FeatureCollection', 'features': mun}, open(os.path.join(out, 'areas', 'municipalities.geojson'), 'w'))
    shutil.copy(countries_path, os.path.join(out, 'areas', 'countries.geojson'))
    print('áreas', a.level.value_counts().to_dict(), flush=True)


if __name__ == '__main__':
    if '--pop-only' in sys.argv:               # território já gerado; troca só a exposição pela do GHSL
        apply_ghsl(os.path.join(sys.argv[1], 'model'), os.path.join(sys.argv[1], 'ext', 'ghsl.zip'))
    elif '--areas-only' in sys.argv:            # território já gerado; refaz só as áreas
        d, cp = sys.argv[1:3]; ext = os.path.join(d, 'ext')
        pop = {s['localidade']['id']: int(s['serie']['2024']) if s['serie']['2024'].isdigit() else 0
               for s in json.load(open(os.path.join(ext, 'pop2024.json')))[0]['resultados'][0]['series']}
        build_areas(os.path.join(d, 'model'), {str(m['id']): m for m in json.load(open(os.path.join(ext, 'mun_meta.json')))}, pop,
                    json.load(open(os.path.join(ext, 'br_mun.geojson')))['features'], json.load(open(os.path.join(ext, 'br_uf.geojson')))['features'],
                    json.load(open(cp))['features'], cp)
    else:
        main(*sys.argv[1:3])
