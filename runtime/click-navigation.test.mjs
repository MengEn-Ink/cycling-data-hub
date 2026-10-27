import assert from "node:assert/strict";
import test from "node:test";
import { clickDirection, isInteractiveTarget, tapAction, tapDirection } from "./click-navigation.js";

test("clickDirection maps the visible left and right halves", () => {
  const bounds = { left: 100, right: 900, width: 800 };
  assert.equal(clickDirection(200, bounds), "previous");
  assert.equal(clickDirection(800, bounds), "next");
  assert.equal(clickDirection(50, bounds), null);
});

test("interactive controls never trigger page navigation", () => {
  assert.equal(isInteractiveTarget({ closest: () => ({ tagName: "BUTTON" }) }), true);
  assert.equal(isInteractiveTarget({ closest: () => null }), false);
});

test("tapDirection accepts a light tap and rejects a drag", () => {
  const bounds = { left: 100, right: 900, width: 800 };
  assert.equal(tapDirection({ x: 700, y: 300 }, { x: 704, y: 304 }, bounds), "next");
  assert.equal(tapDirection({ x: 700, y: 300 }, { x: 730, y: 300 }, bounds), null);
  assert.equal(tapDirection(null, { x: 700, y: 300 }, bounds), null);
});

test("tapAction respects interactive targets before turning a page", () => {
  const bounds = { left: 100, right: 900, width: 800 };
  assert.equal(tapAction({ start: { x: 200, y: 10 }, end: { x: 200, y: 10 }, bounds }), "previous");
  assert.equal(tapAction({ interactive: true, start: { x: 800, y: 10 }, end: { x: 800, y: 10 }, bounds }), null);
});
