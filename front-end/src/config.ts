export const GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best";
export const fireDate = new Date(Date.now() - 3 * 864e5).toISOString().slice(0, 10);

export const CONT: Record<string, { c: string; pt: string; view: [number, number, number] }> = {
  Africa: { c: "#22d3ee", pt: "África", view: [18, 2, 2.6] },
  Europe: { c: "#f472b6", pt: "Europa", view: [15, 52, 3.2] },
  Asia: { c: "#facc15", pt: "Ásia", view: [90, 35, 2.4] },
  "North America": { c: "#fb923c", pt: "América do Norte", view: [-100, 45, 2.4] },
  "South America": { c: "#fb923c", pt: "América do Sul", view: [-60, -18, 2.6] },
  Oceania: { c: "#a855f7", pt: "Oceania", view: [150, -25, 2.8] },
};
export const ORDER = ["Africa", "Europe", "Asia", "North America", "South America", "Oceania"];
export const contColor: any = ["match", ["get", "CONTINENT"], ...ORDER.flatMap((k) => [k, CONT[k].c]), "#8b97a8"];

export const LAYERS = [
  ["sat", "Imagem de satélite"], ["day", "Imagem diária (cor real)"], ["night", "Luzes noturnas"],
  ["fire", "Focos recentes (NASA GIBS)"], ["history", "Atividade histórica (backend)"],
  ["bnd", "Fronteiras políticas"], ["lab", "Rótulos (países)"], ["pop", "População (coroplético)"],
] as const;
export type LayerKey = (typeof LAYERS)[number][0];
