import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(scriptDir, "../..");
const activitiesPath = resolve(projectRoot, "data/activities.json");
const outputPath = resolve(projectRoot, "design-demos/assets/routes-2026.js");

const activities = JSON.parse(readFileSync(activitiesPath, "utf8"));
const routes = activities
  .filter((activity) =>
    (activity.start_date_local || "").startsWith("2026-") &&
    activity.sport_type === "Ride" &&
    activity.summary_polyline
  )
  .map((activity) => ({
    id: activity.id,
    name: activity.name,
    date: activity.start_date_local.slice(0, 10),
    distance_km: Number((activity.distance / 1000).toFixed(1)),
    polyline: activity.summary_polyline,
  }))
  .sort((a, b) => a.date.localeCompare(b.date) || String(a.id).localeCompare(String(b.id)));

const source = [
  "// Generated from data/activities.json by design-demos/scripts/generate-routes-2026.mjs.",
  "// Outdoor Ride activities only; VirtualRide is intentionally excluded from the geographic map.",
  `window.ROUTES_2026=${JSON.stringify(routes)};`,
  "",
].join("\n");

writeFileSync(outputPath, source, "utf8");
console.log(`Wrote ${routes.length} outdoor routes to ${outputPath}`);
