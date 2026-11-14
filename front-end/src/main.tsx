import { createRoot } from "react-dom/client";
import "maplibre-gl/dist/maplibre-gl.css";
import "./styles.css";
import Globe from "./Globe";

createRoot(document.getElementById("root")!).render(<Globe />);
