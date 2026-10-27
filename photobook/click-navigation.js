export function clickDirection(clientX, bounds) {
  if (!bounds || bounds.width <= 0 || clientX < bounds.left || clientX > bounds.right) return null;
  return clientX < bounds.left + bounds.width / 2 ? "previous" : "next";
}

export function isInteractiveTarget(target) {
  return Boolean(target?.closest?.("a,button,input,select,textarea,[role='button'],[data-no-page-click]"));
}

export function tapDirection(start, end, bounds, threshold = 12) {
  if (!start || !end || Math.hypot(end.x - start.x, end.y - start.y) > threshold) return null;
  return clickDirection(end.x, bounds);
}

export function tapAction({ start, end, bounds, interactive = false }) {
  if (interactive) return null;
  return tapDirection(start, end, bounds);
}
