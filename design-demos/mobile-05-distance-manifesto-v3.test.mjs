import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const read = (relative) =>
  readFileSync(new URL(relative, import.meta.url), "utf8");

const html = read("./mobile-05-distance-manifesto-v3.html");
const styles = read("./assets/distance-manifesto-v3.css");
const script = read("./assets/distance-manifesto-v3.js");
const activityAsset = read("./assets/activities-2026.js");
const routeAsset = read("./assets/routes-2026.js");
const sourceActivities = JSON.parse(read("../data/activities.json"));

function loadAsset(source) {
  const sandbox = { window: {} };
  vm.runInNewContext(source, sandbox);
  return sandbox.window;
}

test("V3 assets retain every 2026 activity and only real outdoor routes", () => {
  const publicData = loadAsset(activityAsset).ACTIVITIES_2026;
  const routes = loadAsset(routeAsset).ROUTES_2026;
  const expectedActivities = sourceActivities.filter((activity) =>
    activity.start_date_local?.startsWith("2026-"),
  );
  const expectedRoutes = expectedActivities.filter(
    (activity) => activity.sport_type === "Ride" && activity.summary_polyline,
  );

  assert.equal(publicData.length, expectedActivities.length);
  assert.equal(routes.length, expectedRoutes.length);
  assert.ok(routes.every((route) => route.polyline));
});

test("V3 exposes the complete dashboard interaction contract", () => {
  const chapterIds = [
    "now",
    "rhythm",
    "routes",
    "records",
    "activities",
    "training",
    "book",
    "season",
  ];
  chapterIds.forEach((id) => assert.match(html, new RegExp(`id="${id}"`)));
  [
    "annual-calendar",
    "route-mode",
    "route-focus-list",
    "goal-form",
    "activity-search",
    "activity-sort",
    "activity-detail",
    "open-album",
  ].forEach((id) => assert.match(html, new RegExp(`id="${id}"`)));
  assert.match(html, /data-strava-photobook="1"/);
  assert.match(html, /books\/2026\/photobook\/index\.html/);
  assert.doesNotMatch(html, /\?theme=/);
});

test("annual calendar uses a GitHub-style week grid with real daily metrics", () => {
  assert.match(script, /function calendarGridBounds\(year\)/);
  assert.match(script, /class="github-calendar"/);
  assert.match(script, /class="calendar-weekdays"/);
  assert.match(script, /class="calendar-grid"/);
  assert.match(script, /dayTotals\.get\(key\)/);
  assert.match(styles, /repeat\(var\(--week-count\), minmax\(10px, 1fr\)\)/);
  assert.match(styles, /grid-template-rows: repeat\(7,/);

  const yearStart = new Date(Date.UTC(2026, 0, 1));
  const yearEnd = new Date(Date.UTC(2026, 11, 31));
  const gridStart = new Date(
    yearStart.getTime() - yearStart.getUTCDay() * 86400000,
  );
  const gridEnd = new Date(
    yearEnd.getTime() + (6 - yearEnd.getUTCDay()) * 86400000,
  );
  assert.equal(Math.floor((gridEnd - gridStart) / 604800000) + 1, 53);
});

test("training and gear stay honest without Intervals data", () => {
  assert.match(html, /Intervals\.icu 尚未配置/);
  assert.match(html, /没有证据[^<]*<br \/>就不画曲线/);
  assert.match(html, /尚未同步车辆与部件/);
  assert.match(html, /不生成\s*CTL、ATL、TSB、FTP\s*或功率假数据/);
});

test("responsive layout supports desktop and keeps CJK display type apart", () => {
  assert.match(styles, /@media \(min-width: 960px\)/);
  assert.match(styles, /grid-template-columns: repeat\(12, minmax\(0, 1fr\)\)/);
  assert.match(styles, /font:[^;]+\/1\.13 var\(--display\)/);
  assert.match(styles, /letter-spacing: -0\.018em/);
  assert.match(styles, /word-break: keep-all/);
  [
    "now-data-layout",
    "route-data-layout",
    "records-layout",
    "activities-layout",
    "training-layout",
  ].forEach((className) =>
    assert.match(html, new RegExp(`class="${className}"`)),
  );
});

test("album viewer and embedded book avoid light surfaces", () => {
  assert.match(styles, /\.viewer-shell\s*\{[\s\S]*?background:\s*#0a0807/);
  assert.match(styles, /\.viewer-shell iframe\s*\{[\s\S]*?background:\s*#0a0807/);
  assert.doesNotMatch(styles, /\.viewer-shell\s*\{[\s\S]*?background:\s*#fff/);
});

test("dashboard behavior script parses as standalone JavaScript", () => {
  assert.doesNotThrow(() => new vm.Script(script));
});
