export type Feature = { type: "Feature"; properties: any; geometry: any };
export type FC = { type: "FeatureCollection"; features: Feature[] };
export type BBox = [west: number, south: number, east: number, north: number];
export type Country = { NAME_PT: string; NAME: string; CONTINENT: string; POP_EST: number; TYPE: string; ADM0_A3: string };
export type Selected = { p: Country; bbox: BBox };

// wrap: negative longitudes get +360, so shapes that cross the antimeridian form one contiguous range (east may exceed 180).
export const bboxOf = (coords: any, b: BBox = [180, 90, -180, -90], wrap = false): BBox => {
  if (typeof coords[0] === "number") {
    const x = wrap && coords[0] < 0 ? coords[0] + 360 : coords[0];
    return [Math.min(b[0], x), Math.min(b[1], coords[1]), Math.max(b[2], x), Math.max(b[3], coords[1])];
  }
  return coords.reduce((acc: BBox, c: any) => bboxOf(c, acc, wrap), b);
};
export const countryBounds = (g: any): BBox => {
  const b = bboxOf(g.coordinates);
  return b[2] - b[0] > 180 ? bboxOf(g.coordinates, undefined, true) : b;
};
const bboxArea = (p: any) => { const b = bboxOf(p); return (b[2] - b[0]) * (b[3] - b[1]); };
export const bigPoly = (g: any) => (g.type === "Polygon" ? g.coordinates : g.coordinates.reduce((a: any, p: any) => (bboxArea(p) > bboxArea(a) ? p : a)));

export const norm = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
export const nf = (v: number) => (v >= 1e9 ? `${(v / 1e9).toFixed(2).replace(".", ",")} bi` : v >= 1e6 ? `${(v / 1e6).toFixed(1).replace(".", ",")} mi` : v.toLocaleString("pt-BR"));
