export function firstPageByMonth(pages) {
  const first = new Map();
  Array.from(pages).forEach((page, index) => {
    const month = page.dataset.month;
    if (month && !first.has(month)) first.set(month, index);
  });
  return first;
}

export function activeMonthAtPage(pages, pageIndex, orientation) {
  const visible = orientation === "landscape" && pageIndex > 0
    ? [pageIndex + 1, pageIndex]
    : [pageIndex];
  for (const index of visible) {
    const month = pages[index]?.dataset.month;
    if (month) return month;
  }
  return null;
}
