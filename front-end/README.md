# front-end

Globe front end for flaming-view. Vite + React + TypeScript + MapLibre GL.

## Run

```bash
npm install
npm run dev     # http://localhost:5180
npm run build   # type check + production build
```

## What it shows

- 3D globe with NASA GIBS layers (satellite, daily true color, night lights, VIIRS NOAA-20 thermal anomalies), no API key.
- Country borders and labels from Natural Earth 1:50m (`public/data/countries.geojson`).
- Search bar for countries and coordinates. New data sources plug into the `hits` block in `src/Globe.tsx`.

Labels load glyphs from `demotiles.maplibre.org`, so the globe needs internet.

## Sources

NASA GIBS (tiles), Natural Earth (boundaries), MapLibre GL JS (renderer).
