# front-end

Globe front end for flaming-view. Vite + React + TypeScript + MapLibre GL.

## Run

```bash
npm install
npm run dev     # http://localhost:5180
npm run build   # type check + production build
```

Start the backend separately with `cd ../back-end && make run`. The Vite `/api` proxy forwards local requests to `http://localhost:8000`; set `VITE_API_PROXY_TARGET` in `.env.local` to change that target. For production, set `VITE_API_BASE_URL` to the API URL or configure the web server to proxy `/api` to the backend.

## What it shows

- 3D globe with NASA GIBS layers (satellite, daily true color, night lights, VIIRS NOAA-20 thermal anomalies), no API key.
- Country borders and labels from Natural Earth 1:50m (`public/data/countries.geojson`).
- Search bar for countries and coordinates. New data sources plug into the `hits` block in `src/Globe.tsx`.
- Selecting a country loads `/calendar`, `/series`, `/cells`, `/current`, `/health` and `/method` from the backend.
- Historical cells are rendered as clickable aggregate markers; the panel includes a monthly heatmap, annual uncertainty chart, derived seasonality, live NRT comparison and calendar CSV export.
- Search and geometry still use the bundled Natural Earth GeoJSON because the backend does not yet expose `/areas` or `/areas/{id}/geometry`. Markers represent aggregated cells, not individual fire detections. Forecasts and raw NRT points are not part of the current API.

Labels load glyphs from `demotiles.maplibre.org`, so the globe needs internet.

## Sources

NASA GIBS (tiles), Natural Earth (boundaries), MapLibre GL JS (renderer).
