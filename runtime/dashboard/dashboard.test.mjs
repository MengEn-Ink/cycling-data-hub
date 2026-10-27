import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const root = new URL("./", import.meta.url);
const index = await readFile(new URL("index.html", root), "utf8");
const script = await readFile(new URL("dashboard.js", root), "utf8");
const styles = await readFile(new URL("dashboard.css", root), "utf8");

test("production dashboard keeps release markers and eight real sections", () => {
  assert.match(index, /data-strava-photobook="1"/);
  assert.match(index, /data-cycling-dashboard="1"/);
  assert.match(index, /data-year="__YEAR__"/);
  for (const id of [
    "now",
    "rhythm",
    "routes",
    "records",
    "activities",
    "training",
    "book",
    "season",
  ]) {
    assert.match(index, new RegExp(`<section[^>]+id="${id}"`));
  }
  assert.match(index, /src="__PHOTOBOOK_URL__"/);
  assert.match(index, /__HERO_PHOTO__/);
  assert.match(index, /__ALBUM_PHOTO__/);
});

test("dashboard reads only generated public JSON", () => {
  for (const path of [
    "data/metrics.json",
    "data/activities.json",
    "data/routes.json",
  ]) {
    assert.ok(script.includes(`fetchJson("${path}")`));
  }
  assert.doesNotMatch(script, /window\.(?:ACTIVITIES|ROUTES)_\d{4}/);
  assert.match(script, /metrics\.intervals_available/);
  assert.match(script, /metrics\.gear/);
  assert.match(script, /metrics\.training_load/);
  assert.match(script, /metrics\.ftp_trend/);
  assert.match(script, /metrics\.power_curve/);
});

test("dashboard JavaScript parses without a bundler", () => {
  assert.doesNotThrow(() => new vm.Script(script, { filename: "dashboard.js" }));
  assert.doesNotMatch(`${index}\n${script}\n${styles}`, /react|jsx|vite/i);
});

test("responsive typography protects mobile and desktop layouts", () => {
  assert.match(styles, /@media\s*\(min-width:\s*960px\)/);
  assert.match(styles, /@media\s*\(max-width:\s*360px\)/);
  assert.match(styles, /\.chapter\s*>\s*h2\s*\{[^}]*line-height:\s*1\.1[2-9]/s);
  assert.match(styles, /\.album-copy\s+b\s*\{[^}]*line-height:\s*1\.0[8-9]/s);
  assert.match(styles, /min-height:\s*44px/);
  assert.doesNotMatch(styles, /\.chapter\s*>\s*h2\s*\{[^}]*line-height:\s*0\./s);
});
