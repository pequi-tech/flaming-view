"""Área ativa: país, estado, município (IBGE) ou caixa livre, e como suas células são escolhidas."""
from dataclasses import dataclass

from .area import BBox


@dataclass(frozen=True)
class Area:
    id: str
    level: str                    # country | state | municipality | bbox
    name: str
    bbox: BBox
    parent_id: str | None = None

    def cell_filter(self) -> tuple[str, list]:
        """Condição SQL sobre a tabela de células do modelo (colunas municipality_id, state_id, country)."""
        if self.level == 'municipality':
            return 'municipality_id = ?', [self.id[2:]]
        if self.level == 'state':
            return 'state_id = ?', [self.id[2:]]
        if self.level == 'country':
            return 'country = ?', [self.id]
        return bbox_filter(self.bbox)

    @property
    def in_brazil(self) -> bool:
        return self.id == 'BRA' or self.level in ('state', 'municipality')


def bbox_filter(b: BBox) -> tuple[str, list]:
    lat0, lat1 = b.lat_open_interval()
    lons = b.lon_ranges()
    sql = f"lat > ? AND lat < ? AND ({' OR '.join(['(lon > ? AND lon < ?)'] * len(lons))})"
    return sql, [lat0, lat1] + [v for w, e in lons for v in (w - 0.05, e)]
