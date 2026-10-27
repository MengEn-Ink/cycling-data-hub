import assert from "node:assert/strict";
import test from "node:test";

import { activeMonthAtPage, firstPageByMonth } from "./month-timeline.js";

test("firstPageByMonth keeps the first page for each represented month", () => {
  const pages = [{ dataset: {} }, { dataset: { month: "2" } }, { dataset: { month: "2" } }, { dataset: { month: "5" } }];
  assert.deepEqual([...firstPageByMonth(pages)], [["2", 1], ["5", 3]]);
});

test("activeMonthAtPage reads either visible page in a landscape spread", () => {
  const pages = [{ dataset: {} }, { dataset: { month: "2" } }, { dataset: { month: "2" } }, { dataset: { month: "5" } }];
  assert.equal(activeMonthAtPage(pages, 0, "landscape"), null);
  assert.equal(activeMonthAtPage(pages, 1, "landscape"), "2");
  assert.equal(activeMonthAtPage(pages, 3, "portrait"), "5");
});

test("a landscape spread crossing months highlights the newer right page", () => {
  const pages = [{ dataset: {} }, { dataset: { month: "7" } }, { dataset: { month: "8" } }];
  assert.equal(activeMonthAtPage(pages, 1, "landscape"), "8");
});
