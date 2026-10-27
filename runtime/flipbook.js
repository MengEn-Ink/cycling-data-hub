import { activeMonthAtPage, firstPageByMonth } from "./month-timeline.js";
import { isInteractiveTarget, tapAction } from "./click-navigation.js";

const bookElement = document.querySelector("#book");
const pages = bookElement.querySelectorAll(".book-page");
const previousButton = document.querySelector("#previous");
const nextButton = document.querySelector("#next");
const pageStatus = document.querySelector("#page-status");
const orientationStatus = document.querySelector("#orientation");
const pageWidth = Number(bookElement.dataset.pageWidth) || 512;
const pageHeight = Number(bookElement.dataset.pageHeight) || 640;
const monthButtons = [...document.querySelectorAll(".month-jump")];
const monthPages = firstPageByMonth(pages);
const locationParams = new URLSearchParams(location.search);
document.documentElement.style.setProperty("--page-ratio", pageWidth / pageHeight);

const pageFlip = new St.PageFlip(bookElement, {
  width: pageWidth,
  height: pageHeight,
  size: "stretch",
  minWidth: Math.max(1, Math.round(pageWidth * 0.56)),
  maxWidth: Math.max(1, Math.round(pageWidth * 1.04)),
  minHeight: Math.max(1, Math.round(pageHeight * 0.56)),
  maxHeight: Math.max(1, Math.round(pageHeight * 1.04)),
  drawShadow: false,
  flippingTime: 460,
  usePortrait: true,
  startZIndex: 10,
  autoSize: true,
  maxShadowOpacity: 0.42,
  showCover: true,
  mobileScrollSupport: false,
  clickEventForward: true,
  useMouseEvents: true,
  swipeDistance: 24,
  showPageCorners: true,
  disableFlipByClick: true,
});

let currentPage = 0;
let isTurning = false;
let currentOrientation = "landscape";

function updateMonthTimeline() {
  const activeMonth = activeMonthAtPage(pages, currentPage, currentOrientation);
  monthButtons.forEach((button) => {
    if (button.dataset.month === activeMonth) button.setAttribute("aria-current", "true");
    else button.removeAttribute("aria-current");
  });
}

function updateControls() {
  const pageCount = pageFlip.getPageCount();
  const lastPage = pageCount - 1;
  bookElement.dataset.edge = currentPage === 0 ? "front" : currentPage === lastPage ? "back" : "inside";

  previousButton.disabled = currentPage === 0 || isTurning;
  nextButton.disabled = currentPage === lastPage || isTurning;

  if (currentPage === 0) {
    pageStatus.textContent = "Cover";
  } else if (currentPage === lastPage) {
    pageStatus.textContent = "Back cover";
  } else {
    pageStatus.textContent = `${String(currentPage + 1).padStart(2, "0")} / ${String(pageCount).padStart(2, "0")}`;
  }
  updateMonthTimeline();
}

pageFlip.on("flip", (event) => {
  currentPage = Number(event.data);
  updateControls();
});

pageFlip.on("changeState", (event) => {
  isTurning = event.data !== "read";
  updateControls();
});

function updateOrientation(orientation) {
  currentOrientation = orientation;
  bookElement.dataset.layout = orientation;
  if (orientationStatus) orientationStatus.textContent = orientation === "portrait" ? "Single page" : "Open spread";
  updateMonthTimeline();
}

pageFlip.on("init", (event) => updateOrientation(event.data.mode));
pageFlip.on("changeOrientation", (event) => updateOrientation(event.data));

pageFlip.loadFromHTML(pages);
updateControls();

const requestedPage = Number(locationParams.get("page"));
if (Number.isInteger(requestedPage) && requestedPage >= 0 && requestedPage < pages.length) {
  pageFlip.turnToPage(requestedPage);
}

previousButton.addEventListener("click", () => {
  if (!isTurning) pageFlip.flipPrev("bottom");
});

nextButton.addEventListener("click", () => {
  if (!isTurning) pageFlip.flipNext("bottom");
});

monthButtons.forEach((button) => button.addEventListener("click", () => {
  const page = monthPages.get(button.dataset.month);
  if (!isTurning && Number.isInteger(page)) pageFlip.turnToPage(page);
}));

let pointerStart = null;
bookElement.addEventListener("pointerdown", (event) => {
  pointerStart = { x: event.clientX, y: event.clientY };
}, { capture: true });
bookElement.addEventListener("pointerup", (event) => {
  const action = tapAction({
    start: pointerStart,
    end: { x: event.clientX, y: event.clientY },
    bounds: bookElement.getBoundingClientRect(),
    interactive: isInteractiveTarget(event.target),
  });
  pointerStart = null;
  if (!action || isTurning) return;
  event.preventDefault();
  event.stopPropagation();
  if (action === "previous") pageFlip.flipPrev("bottom");
  if (action === "next") pageFlip.flipNext("bottom");
}, { capture: true });

window.addEventListener("keydown", (event) => {
  if (event.altKey || event.ctrlKey || event.metaKey || isTurning) return;

  if (event.key === "ArrowLeft") {
    event.preventDefault();
    pageFlip.flipPrev("bottom");
  }

  if (event.key === "ArrowRight" || event.key === " ") {
    event.preventDefault();
    pageFlip.flipNext("bottom");
  }

  if (event.key === "Home") pageFlip.turnToPage(0);
  if (event.key === "End") pageFlip.turnToPage(pageFlip.getPageCount() - 1);
});
