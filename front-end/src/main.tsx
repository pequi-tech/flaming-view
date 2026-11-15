import { createRoot } from "react-dom/client";
import "maplibre-gl/dist/maplibre-gl.css";
import "./fv.css";
import App from "./App";
import { ReportDoc } from "./views/Report";

const q = new URLSearchParams(location.search);
createRoot(document.getElementById("root")!).render(location.pathname === "/report"
  ? <ReportDoc areaId={q.get("area") ?? "BRA"} horizon={Number(q.get("horizon") ?? 1)} autoPrint={q.get("print") === "1"} />
  : <App />);
