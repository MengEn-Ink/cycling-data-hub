import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const html = readFileSync(
  new URL("./mobile-05-distance-manifesto-v2.html", import.meta.url),
  "utf8",
);
const activities = JSON.parse(
  readFileSync(new URL("../data/activities.json", import.meta.url), "utf8"),
);
const routeAsset = readFileSync(
  new URL("./assets/routes-2026.js", import.meta.url),
  "utf8",
);
const sandbox = { window: {} };
vm.runInNewContext(routeAsset, sandbox);

test("route heatmap asset contains every 2026 outdoor ride with a real polyline", () => {
  const expected = activities.filter(
    (activity) =>
      activity.start_date_local?.startsWith("2026-") &&
      activity.sport_type === "Ride" &&
      activity.summary_polyline,
  );
  const actual = sandbox.window.ROUTES_2026;

  assert.equal(actual.length, expected.length);
  assert.deepEqual(
    new Set(actual.map((route) => String(route.id))),
    new Set(expected.map((activity) => String(activity.id))),
  );
  assert.ok(actual.every((route) => route.polyline.length > 0));
});

test("prototype uses a geographic route canvas and removes the calendar heatmap", () => {
  assert.match(html, /id="route-heatmap"/);
  assert.match(html, /assets\/routes-2026\.js/);
  assert.match(html, /亮度 = 路线重合频次/);
  assert.doesNotMatch(html, /id="ride-heatmap"/);
  assert.doesNotMatch(html, /id="heat-data"/);
  assert.doesNotMatch(html, /每日累计距离/);
});

test("route heatmap copy explains the honest outdoor-only data scope", () => {
  const outdoorCount = activities.filter(
    (activity) =>
      activity.start_date_local?.startsWith("2026-") &&
      activity.sport_type === "Ride" &&
      activity.summary_polyline,
  ).length;
  const virtualCount = activities.filter(
    (activity) =>
      activity.start_date_local?.startsWith("2026-") &&
      activity.sport_type === "VirtualRide",
  ).length;
  assert.match(html, new RegExp(`${outdoorCount} 条户外骑行的真实轨迹叠加`));
  assert.match(html, new RegExp(`${virtualCount}\\s*条室内骑行不参与地理绘制`));
  assert.match(html, /不代表速度或训练强度/);
});
