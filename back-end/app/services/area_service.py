"""Casos de uso das áreas: resolver a área ativa (id ou caixa), buscar por nome e devolver a geometria."""
import unicodedata

from ..domain.area import BBox
from ..domain.errors import InvalidArea, NotFound
from ..domain.territory import Area
from ..infra.geometries import Geometries
from ..infra.model_store import ModelStore


def fold(text: str) -> str:
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode().lower().strip()


class AreaService:
    def __init__(self, store: ModelStore, geometries: Geometries):
        self.store, self.geometries = store, geometries

    def resolve(self, area_id: str | None, bbox: BBox | None) -> Area:
        if area_id:
            a = self.store.area(area_id)
            return Area(a['area_id'], a['level'], a['name'], BBox(a['w'], a['s'], a['e'], a['n']), a['parent_id'])
        if bbox is None:
            raise InvalidArea('informe area_id ou bbox')
        return Area(str(bbox), 'bbox', str(bbox), bbox)

    def search(self, q: str, limit: int = 8) -> dict:
        return {'query': q, 'areas': self.store.search(fold(q), limit) if fold(q) else []}

    def geometry(self, area_id: str) -> dict:
        f = self.geometries.get(area_id)
        if f is None:
            raise NotFound(f'geometria de {area_id} não existe')
        return f['geometry']

    def lineage(self, area: Area) -> list[dict]:
        """Brasil › Goiás › Rio Verde, para o breadcrumb."""
        chain, cur = [], area
        while cur.parent_id:
            p = self.store.area(cur.parent_id)
            chain.insert(0, {'id': p['area_id'], 'name': p['name'], 'level': p['level']})
            cur = Area(p['area_id'], p['level'], p['name'], cur.bbox, p['parent_id'])
        return chain + [{'id': area.id, 'name': area.name, 'level': area.level}]
