"""Previsão + território da release numa tabela em memória `cp` (uma linha por célula 0,05°, horizontes em colunas).

O IPP é calculado aqui no boot com os pesos de domain/ipp_params (não é materializado na release), e os cortes
globais saem dos quantis desse cálculo. Consultas por área usam o filtro de domain/territory.Area.
"""
from ..domain.errors import ModelUnavailable, NotFound
from ..domain.ipp_params import CUT_QUANTILES, FLOOR, WEIGHTS
from .release import Release

K = "CASE {c} WHEN 'baixo' THEN 0 WHEN 'normal' THEN 1 WHEN 'alto' THEN 2 ELSE 3 END"
H = (1, 2, 3)


class ModelStore:
    def __init__(self, release: Release):
        self.release, self.db = release, release.db
        self.ready = release.has_model
        self.cuts, self.areas = {}, {}
        if not self.ready:
            return
        p = lambda name: str(release.path / name)
        ipp = lambda h: (f"pow(greatest(n{h}, {FLOOR}), {WEIGHTS['n']}) * pow(greatest(v, {FLOOR}), {WEIGHTS['v']})"
                         f" * pow(greatest(e, {FLOOR}), {WEIGHTS['e']})")
        cols = ', '.join(f"p{h}.class AS c{h}, {K.format(c=f'p{h}.class')} AS k{h}, p{h}.predicted AS p{h}, p{h}.lo AS lo{h}, "
                         f"p{h}.hi AS hi{h}, p{h}.n AS n{h}, p{h}.ratio AS r{h}, p{h}.forecast_month AS m{h}" for h in H)
        joins = ' '.join(f"JOIN read_parquet('{p('predictions.parquet')}') p{h} ON p{h}.cell_id = t.cell_id AND p{h}.horizon = {h}" for h in H)
        # fatores NASA POWER (opcionais): célula do modelo = canto SW em múltiplos de `res`
        res = release.model_metrics.get('resolution_used', 0.5)
        wx, wxjoin = 'NULL::FLOAT AS rain, NULL::FLOAT AS t2m, NULL::FLOAT AS rh2m, NULL::FLOAT AS wind, NULL::VARCHAR AS wx_months', ''
        if 'drivers.parquet' in release.manifest['files']:
            wx = 'd.rain, d.t2m, d.rh2m, d.wind, d.months AS wx_months'
            wxjoin = (f"LEFT JOIN read_parquet('{p('drivers.parquet')}') d ON d.lat = round(floor(t.lat / {res}) * {res}, 3)"
                      f" AND d.lon = round(floor(t.lon / {res}) * {res}, 3)")
        self.db.execute(f"""CREATE TABLE cp AS SELECT t.*, {cols}, p1.recent_data AS recent, p1.model_version AS model_version, {wx}
                            FROM read_parquet('{p('territory.parquet')}') t {joins} {wxjoin}""")
        self.db.execute('ALTER TABLE cp ADD COLUMN ipp1 FLOAT; ALTER TABLE cp ADD COLUMN ipp2 FLOAT; ALTER TABLE cp ADD COLUMN ipp3 FLOAT')
        self.db.execute(f"UPDATE cp SET {', '.join(f'ipp{h} = {ipp(h)}' for h in H)}")
        self.db.execute(f"CREATE TABLE areas AS SELECT * FROM read_parquet('{p('areas.parquet')}')")
        q = list(CUT_QUANTILES.values())
        for h in H:
            vals = self.db.execute(f'SELECT quantile_cont(ipp{h}, {q}) FROM cp').fetchone()[0]
            self.cuts[h] = {k: round(float(v), 4) for k, v in zip(CUT_QUANTILES, vals)}

    def _need(self):
        if not self.ready:
            raise ModelUnavailable('release sem previsão (contrato 1.0)')

    def rows(self, sql: str, params: list) -> list[dict]:
        self._need()
        cur = self.db.cursor().execute(sql, params)
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]

    def area(self, area_id: str) -> dict:
        self._need()
        r = self.rows('SELECT * FROM areas WHERE area_id = ?', [area_id])
        if not r:
            raise NotFound(f'área {area_id} não existe')
        return r[0]

    def search(self, q: str, limit: int) -> list[dict]:
        return self.rows("""SELECT area_id, level, name, parent_id FROM areas
            WHERE search LIKE ? OR search LIKE ?
            ORDER BY NOT starts_with(search, ?), CASE level WHEN 'country' THEN 0 WHEN 'state' THEN 1 ELSE 2 END,
                     population DESC NULLS LAST, name LIMIT ?""", [f'{q}%', f'% {q}%', q, limit])

    def cell(self, cell_id: int) -> dict:
        r = self.rows('SELECT * FROM cp WHERE cell_id = ?', [cell_id])
        if not r:
            raise NotFound(f'célula {cell_id} sem histórico nem previsão')
        return r[0]

    def names(self, ids: list[str]) -> dict:
        return {r['area_id']: r['name'] for r in self.rows('SELECT area_id, name FROM areas WHERE list_contains(?, area_id)', [ids])} if ids else {}

    def forecast(self, where: str, params: list, h: int) -> list[dict]:
        return self.rows(f"""SELECT c{h} AS level, count(*) AS cells, sum(p{h}) AS predicted, sum(lo{h}) AS lo, sum(hi{h}) AS hi,
            any_value(m{h}) AS forecast_month, bool_and(recent) AS recent, any_value(model_version) AS model_version
            FROM cp WHERE {where} GROUP BY ALL""", params)

    def cells(self, where: str, params: list, h: int, layer: str, h3_res: int | None) -> list[dict]:
        v = f'ipp{h}' if layer == 'ipp' else f'p{h}'
        if h3_res is None:
            keep = '' if layer == 'ipp' else f' AND (p{h} > 0.01 OR k{h} = 3)'
            return self.rows(f"SELECT cell_id::VARCHAR AS id, lat, lon, {v} AS value, k{h} AS k FROM cp WHERE {where}{keep}", params)
        agg = f'avg({v})' if layer == 'ipp' else f'sum({v})'
        k = 'NULL' if layer == 'ipp' else f'coalesce(round(sum(k{h} * (p{h} + 0.001)) / sum(p{h} + 0.001)), 1)'
        return self.rows(f"""SELECT h3_{h3_res} AS id, avg(lat) + 0.025 AS lat, avg(lon) + 0.025 AS lon, {agg} AS value, {k} AS k
            FROM cp WHERE {where} GROUP BY 1""", params)

    def history_h3(self, where: str, params: list, year: int, month: int, h3_res: int) -> list[dict]:
        self._need()
        return self.rows(f"""SELECT c.h3_{h3_res} AS id, avg(c.lat) + 0.025 AS lat, avg(c.lon) + 0.025 AS lon,
            sum(g.activity) AS value, NULL AS k FROM grid g JOIN cp c USING (cell_id)
            WHERE g.year = ? AND g.month = ? AND {where.replace('lat', 'c.lat').replace('lon', 'c.lon')} GROUP BY 1""",
            [year, month] + params)

    def priorities(self, where: str, params: list, h: int, key: str) -> list[dict]:
        """Todos os grupos (município, célula ou hexágono) da área, com o contexto das regras R1–R7. Ordem e corte ficam no serviço."""
        return self.rows(f"""SELECT {key}::VARCHAR AS id, max(ipp{h}) AS ipp, arg_max(n{h}, ipp{h}) AS n, arg_max(v, ipp{h}) AS v,
            arg_max(e, ipp{h}) AS e, sum(p{h}) AS predicted, count(*) AS cells, count_if(k{h} = 3) AS critical,
            max(k1) AS k1, max(k2) AS k2, max(k3) AS k3, bool_or(k1 >= 2 AND e >= 0.75) AS exposed_high,
            bool_or(e_ti >= 1 AND greatest(k1, k2, k3) = 3) AS ti_critical, bool_or(v >= 0.75 AND k1 = 1) AS recurrent_normal, min(rain) AS rain,
            avg((k1 = 3)::INT) AS crit_share, any_value(ti_name) FILTER (WHERE ti_name IS NOT NULL) AS ti_name,
            avg(lat) + 0.025 AS lat, avg(lon) + 0.025 AS lon
            FROM cp WHERE {where} AND {key} IS NOT NULL GROUP BY 1""", params)
