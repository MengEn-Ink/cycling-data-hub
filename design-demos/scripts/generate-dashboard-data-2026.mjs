import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(scriptDir, "../..");
const activitiesPath = resolve(projectRoot, "data/activities.json");
const assetsDir = resolve(projectRoot, "design-demos/assets");

const records = JSON.parse(readFileSync(activitiesPath, "utf8"));
const activities = records
  .filter((activity) => (activity.start_date_local || "").startsWith("2026-"))
  .map((activity) => ({
    id: String(activity.id),
    name: activity.name || "未命名骑行",
    date: (activity.start_date_local || "").slice(0, 10),
    sport_type: activity.sport_type || activity.type || "Ride",
    distance_km: Number(((activity.distance || 0) / 1000).toFixed(1)),
    elev_m: Math.round(activity.total_elevation_gain || 0),
    moving_seconds: Math.round(activity.moving_time || 0),
    avg_speed_kmh: Number(((activity.average_speed || 0) * 3.6).toFixed(1)),
    kudos: Math.round(activity.kudos_count || 0),
    comments: Math.round(activity.comment_count || 0),
    athletes: Math.round(activity.athlete_count || 1),
    pr_count: Math.round(activity.pr_count || 0),
    achievements: Math.round(activity.achievement_count || 0),
    photo_count: Math.round(
      activity.total_photo_count || activity.photo_count || 0,
    ),
    polyline: activity.summary_polyline || "",
  }))
  .sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id));

const routes = activities
  .filter((activity) => activity.sport_type === "Ride" && activity.polyline)
  .map(({ id, name, date, distance_km, polyline }) => ({
    id,
    name,
    date,
    distance_km,
    polyline,
  }))
  .sort((a, b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id));

function writeAsset(filename, variable, data, note) {
  const source = [
    `// Generated from data/activities.json by design-demos/scripts/generate-dashboard-data-2026.mjs.`,
    `// ${note}`,
    `window.${variable}=${JSON.stringify(data)};`,
    "",
  ].join("\n");
  writeFileSync(resolve(assetsDir, filename), source, "utf8");
}

writeAsset(
  "activities-2026.js",
  "ACTIVITIES_2026",
  activities,
  "Public prototype fields only; no credentials or raw API response.",
);
writeAsset(
  "routes-2026.js",
  "ROUTES_2026",
  routes,
  "Outdoor Ride activities with summary_polyline only; VirtualRide is excluded.",
);

console.log(
  `Wrote ${activities.length} activities and ${routes.length} outdoor routes to ${assetsDir}`,
);
