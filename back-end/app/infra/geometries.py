"""GeoJSON simplificados das áreas (países, estados, municípios), lidos uma vez e indexados por area_id."""
import json
from pathlib import Path


class Geometries:
    FILES = {'countries.geojson': 'ADM0_A3', 'states.geojson': 'area_id', 'municipalities.geojson': 'area_id'}

    def __init__(self, release_path: Path):
        self.root, self._by_id = Path(release_path) / 'areas', None

    def get(self, area_id: str) -> dict | None:
        if self._by_id is None:                       # ponytail: ~5 MB em memória; carregar sob demanda se crescer
            self._by_id = {}
            for name, key in self.FILES.items():
                p = self.root / name
                if p.exists():
                    for f in json.loads(p.read_text())['features']:
                        self._by_id[f['properties'][key]] = f
        return self._by_id.get(area_id)
