(async () => {
  "use strict";

  const year = document.documentElement.dataset.year || "2026";
  const dataStatus = document.getElementById("data-status");
  async function fetchJson(path) {
    const response = await fetch(path, { cache: "no-cache" });
    if (!response.ok) throw new Error(path + " -> " + response.status);
    return response.json();
  }

  let activities = [];
  let routes = [];
  let metrics = {};
  try {
    [metrics, activities, routes] = await Promise.all([
      fetchJson("data/metrics.json"),
      fetchJson("data/activities.json"),
      fetchJson("data/routes.json"),
    ]);
  } catch (error) {
    dataStatus.dataset.state = "error";
    dataStatus.textContent = "公开数据读取失败，请稍后刷新。";
    console.error("dashboard data unavailable", error);
    return;
  }
  activities = Array.isArray(activities) ? activities : [];
  routes = Array.isArray(routes) ? routes : [];
  metrics = metrics && typeof metrics === "object" ? metrics : {};
  const activityById = new Map(
    activities.map((activity) => [String(activity.id), activity]),
  );
  const monthNames = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
  ];
  const zhMonths = [
    "1月",
    "2月",
    "3月",
    "4月",
    "5月",
    "6月",
    "7月",
    "8月",
    "9月",
    "10月",
    "11月",
    "12月",
  ];
  const number = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 1 });
  const integer = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 });

  function byId(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function dateValue(raw) {
    return Date.parse(raw + "T00:00:00Z");
  }

  function dateLabel(raw) {
    const [, month, day] = raw.split("-");
    return Number(month) + "月" + Number(day) + "日";
  }

  function monthKey(activity) {
    return activity.date.slice(0, 7);
  }

  function hours(seconds) {
    return Number((seconds / 3600).toFixed(1));
  }

  function signedPercent(current, previous) {
    if (!previous) return current ? "+100.0%" : "0.0%";
    const change = ((current - previous) / previous) * 100;
    return (change >= 0 ? "+" : "−") + Math.abs(change).toFixed(1) + "%";
  }

  function aggregate(records) {
    return records.reduce(
      (sum, activity) => {
        sum.rides += 1;
        sum.distance += activity.distance_km;
        sum.elevation += activity.elev_m;
        sum.seconds += activity.moving_seconds;
        sum.kudos += activity.kudos;
        return sum;
      },
      { rides: 0, distance: 0, elevation: 0, seconds: 0, kudos: 0 },
    );
  }

  function groupDays(records) {
    const days = new Map();
    records.forEach((activity) => {
      const day = days.get(activity.date) || {
        distance: 0,
        elevation: 0,
        rides: 0,
      };
      day.distance += activity.distance_km;
      day.elevation += activity.elev_m;
      day.rides += 1;
      days.set(activity.date, day);
    });
    return days;
  }

  function eddington(records) {
    const daily = [...groupDays(records).values()]
      .map((day) => day.distance)
      .sort((a, b) => b - a);
    let current = 0;
    daily.forEach((distance, index) => {
      if (distance >= index + 1) current = index + 1;
    });
    const target = current + 1;
    const qualifying = daily.filter((distance) => distance >= target).length;
    return { current, target, needsDays: target - qualifying };
  }

  const totals = aggregate(activities);
  const dayTotals = groupDays(activities);
  const eddingtonState = eddington(activities);

  function renderHero() {
    const kpis = metrics.kpis || {};
    const distance = Number(kpis.distance_km ?? totals.distance).toFixed(1);
    const [main, decimal] = number.format(Number(distance)).split(".");
    byId("hero-distance-main").textContent = main;
    byId("hero-distance-decimal").textContent = "." + (decimal || "0");
    byId("hero-rides").textContent = kpis.rides ?? totals.rides;
    byId("kpi-rides").textContent = kpis.rides ?? totals.rides;
    byId("kpi-elev").textContent = integer.format(kpis.elev_m ?? totals.elevation);
    byId("kpi-hours").textContent = hours(kpis.moving_seconds ?? totals.seconds).toFixed(1);
    byId("kpi-kudos").textContent = integer.format(kpis.kudos ?? totals.kudos);
    byId("kpi-longest").textContent =
      number.format(kpis.longest_km ?? Math.max(0, ...activities.map((activity) => activity.distance_km))) + " km";
    byId("kpi-eddington").textContent = metrics.eddington ?? eddingtonState.current;
    byId("activity-headline-count").textContent = integer.format(kpis.rides ?? totals.rides);
  }

  function recordsInRange(start, end) {
    return activities.filter((activity) => {
      const value = dateValue(activity.date);
      return value >= start && value <= end;
    });
  }

  function renderRecent() {
    if (!activities.length) return;
    const latest = [...activities].sort((a, b) =>
      b.date.localeCompare(a.date),
    )[0].date;
    const end = dateValue(latest);
    const day = 86400000;
    const current = aggregate(recordsInRange(end - 6 * day, end));
    const previous = aggregate(recordsInRange(end - 13 * day, end - 7 * day));
    const startDate = new Date(end - 6 * day);
    const endDate = new Date(end);
    const range =
      monthNames[startDate.getUTCMonth()] +
      " " +
      String(startDate.getUTCDate()).padStart(2, "0") +
      " — " +
      monthNames[endDate.getUTCMonth()] +
      " " +
      String(endDate.getUTCDate()).padStart(2, "0");
    byId("latest-sync").textContent = "同步至 " + latest.replaceAll("-", ".");
    byId("recent-range").textContent = range;
    byId("recent-distance").textContent = number.format(current.distance);
    const delta =
      ((current.distance - previous.distance) / (previous.distance || 1)) * 100;
    const deltaNode = byId("recent-delta");
    deltaNode.textContent =
      "较此前 7 天 " + signedPercent(current.distance, previous.distance);
    deltaNode.classList.toggle("positive", delta >= 0);
    byId("recent-rides").textContent = current.rides + " 次";
    byId("recent-elev").textContent = integer.format(current.elevation) + " m";
    byId("recent-hours").textContent = hours(current.seconds).toFixed(1) + " h";
    byId("previous-distance").textContent =
      number.format(previous.distance) + " km";
  }

  const monthly = new Map();
  activities.forEach((activity) => {
    const key = monthKey(activity);
    const data = monthly.get(key) || {
      rides: 0,
      distance: 0,
      elevation: 0,
      seconds: 0,
    };
    data.rides += 1;
    data.distance += activity.distance_km;
    data.elevation += activity.elev_m;
    data.seconds += activity.moving_seconds;
    monthly.set(key, data);
  });

  function selectMonthBar(button) {
    document
      .querySelectorAll(".bar-option")
      .forEach((item) =>
        item.setAttribute("aria-pressed", String(item === button)),
      );
    const data = monthly.get(button.dataset.key);
    byId("active-month").textContent =
      Number(button.dataset.month) + "月 / DISTANCE";
    byId("active-distance").textContent = number.format(data.distance);
    byId("active-elevation").textContent =
      integer.format(data.elevation) + " m 爬升";
    byId("active-rides").textContent = data.rides + " 次骑行";
  }

  function renderRhythm() {
    const entries = [...monthly.entries()].sort(([a], [b]) =>
      a.localeCompare(b),
    );
    if (!entries.length) {
      byId("bar-chart").innerHTML = '<p class="intro">本年度暂无骑行记录。</p>';
      return;
    }
    const maximum = Math.max(...entries.map(([, data]) => data.distance));
    const chart = byId("bar-chart");
    chart.innerHTML = entries
      .map(([key, data]) => {
        const month = key.slice(5);
        const height = Math.max(4, (data.distance / maximum) * 100).toFixed(1);
        return (
          '<button class="bar-option" type="button" data-key="' +
          key +
          '" data-month="' +
          month +
          '" aria-label="' +
          Number(month) +
          "月，" +
          number.format(data.distance) +
          "公里，爬升" +
          integer.format(data.elevation) +
          "米，" +
          data.rides +
          '次骑行" aria-pressed="false"><i class="bar" style="--h:' +
          height +
          '%"></i><span>' +
          month +
          "</span></button>"
        );
      })
      .join("");
    chart
      .querySelectorAll(".bar-option")
      .forEach((button) =>
        button.addEventListener("click", () => selectMonthBar(button)),
      );
    const peak = entries.reduce((best, entry) =>
      entry[1].distance > best[1].distance ? entry : best,
    );
    const peakMonth = Number(peak[0].slice(5));
    byId("peak-month-note").textContent = peakMonth + " 月是年度距离峰值。";
    byId("peak-month-detail").textContent =
      number.format(peak[1].distance) +
      " km / " +
      integer.format(peak[1].elevation) +
      " m；来自本地 Strava 缓存。";
    const defaultButton = chart.querySelector('[data-key="' + peak[0] + '"]');
    if (defaultButton) selectMonthBar(defaultButton);
  }

  let calendarMetric = "distance";
  const calendarYear = Number(year);
  const dayMs = 86400000;
  const weekMs = dayMs * 7;

  function calendarLevel(value) {
    const limits =
      calendarMetric === "distance" ? [0, 30, 70, 120] : [0, 300, 800, 1500];
    if (!value) return 0;
    if (value <= limits[1]) return 1;
    if (value <= limits[2]) return 2;
    if (value <= limits[3]) return 3;
    return 4;
  }

  function calendarGridBounds(year) {
    const yearStart = new Date(Date.UTC(year, 0, 1));
    const yearEnd = new Date(Date.UTC(year, 11, 31));
    const gridStart = new Date(
      yearStart.getTime() - yearStart.getUTCDay() * dayMs,
    );
    const gridEnd = new Date(
      yearEnd.getTime() + (6 - yearEnd.getUTCDay()) * dayMs,
    );
    return {
      gridStart,
      weekCount: Math.floor((gridEnd - gridStart) / weekMs) + 1,
    };
  }

  function renderCalendar() {
    const calendar = byId("annual-calendar");
    const { gridStart, weekCount } = calendarGridBounds(calendarYear);
    const monthLabels = [];
    for (let month = 0; month < 12; month += 1) {
      const monthStart = new Date(Date.UTC(calendarYear, month, 1));
      const week = Math.floor((monthStart - gridStart) / weekMs) + 1;
      monthLabels.push(
        '<span style="grid-column:' + week + '">' + zhMonths[month] + "</span>",
      );
    }

    const weekdayLabels = ["", "一", "", "三", "", "五", ""];
    const cells = [];
    for (let offset = 0; offset < weekCount * 7; offset += 1) {
      const date = new Date(gridStart.getTime() + offset * dayMs);
      const week = Math.floor(offset / 7) + 1;
      const weekday = (offset % 7) + 1;
      const inYear = date.getUTCFullYear() === calendarYear;
      if (!inYear) {
        cells.push(
          '<i class="calendar-day out" style="grid-column:' +
            week +
            ";grid-row:" +
            weekday +
            '" aria-hidden="true"></i>',
        );
        continue;
      }

      const key = date.toISOString().slice(0, 10);
      const record = dayTotals.get(key);
      const value = record ? record[calendarMetric] : 0;
      const unit = calendarMetric === "distance" ? "km" : "m";
      cells.push(
        '<i class="calendar-day l' +
          calendarLevel(value) +
          '" style="grid-column:' +
          week +
          ";grid-row:" +
          weekday +
          '" title="' +
          key +
          " · " +
          number.format(value) +
          " " +
          unit +
          '" aria-hidden="true"></i>',
      );
    }

    calendar.innerHTML =
      '<div class="github-calendar" style="--week-count:' +
      weekCount +
      '"><div class="calendar-months">' +
      monthLabels.join("") +
      '</div><div class="calendar-grid-wrap"><div class="calendar-weekdays" aria-hidden="true">' +
      weekdayLabels.map((label) => "<span>" + label + "</span>").join("") +
      '</div><div class="calendar-grid">' +
      cells.join("") +
      "</div></div></div>";

    const values = [...dayTotals.values()].map((day) => day[calendarMetric]);
    const peak = Math.max(0, ...values);
    byId("active-days").textContent = dayTotals.size;
    byId("calendar-peak").textContent =
      "最高单日 " +
      number.format(peak) +
      (calendarMetric === "distance" ? " km" : " m 爬升");
    calendar.setAttribute(
      "aria-label",
      year + " 全年骑行日历，" +
        dayTotals.size +
        " 个骑行日，按星期与周排列，颜色表示每日" +
        (calendarMetric === "distance" ? "里程" : "爬升"),
    );
  }

  document.querySelectorAll("[data-calendar-metric]").forEach((button) => {
    button.addEventListener("click", () => {
      calendarMetric = button.dataset.calendarMetric;
      document
        .querySelectorAll("[data-calendar-metric]")
        .forEach((item) =>
          item.setAttribute("aria-pressed", String(item === button)),
        );
      renderCalendar();
    });
  });

  function renderRecords() {
    if (!activities.length) {
      byId("record-list").innerHTML = '<p class="intro">本年度暂无可用纪录。</p>';
      return;
    }
    const best = (key) => [...activities].sort((a, b) => b[key] - a[key])[0];
    const records = [
      {
        label: "LONGEST RIDE",
        activity: best("distance_km"),
        value: (activity) => number.format(activity.distance_km) + " km",
      },
      {
        label: "MOST ELEVATION",
        activity: best("elev_m"),
        value: (activity) => integer.format(activity.elev_m) + " m",
      },
      {
        label: "FASTEST AVERAGE",
        activity: best("avg_speed_kmh"),
        value: (activity) => number.format(activity.avg_speed_kmh) + " km/h",
      },
      {
        label: "MOST KUDOS",
        activity: best("kudos"),
        value: (activity) => integer.format(activity.kudos),
      },
    ];
    byId("record-list").innerHTML = records
      .map(
        ({ label, activity, value }) =>
          '<article class="record-item"><div><span>' +
          label +
          "</span><h3>" +
          escapeHtml(activity.name) +
          "</h3><p>" +
          dateLabel(activity.date) +
          '</p></div><b class="data">' +
          value(activity) +
          "</b></article>",
      )
      .join("");
    const currentEddington = metrics.eddington ?? eddingtonState.current;
    byId("eddington-current").textContent = "E" + currentEddington;
    byId("eddington-next").textContent =
      "再补 " +
      eddingtonState.needsDays +
      " 个 ≥" +
      eddingtonState.target +
      " km 的骑行日，可到 E" +
      eddingtonState.target +
      "。";
  }

  const goalInput = byId("goal-input");
  function readGoal() {
    try {
      return Number(localStorage.getItem("distance-manifesto-" + year + "-goal") || 0);
    } catch (_) {
      return 0;
    }
  }

  function renderGoal(goal) {
    const progress = byId("goal-progress");
    if (!goal) {
      byId("goal-state").textContent = "尚未设置";
      byId("goal-copy").textContent =
        "目标只保存在当前浏览器，不会伪装成服务器数据。";
      progress.hidden = true;
      return;
    }
    const percent = Math.min(100, (totals.distance / goal) * 100);
    goalInput.value = String(goal);
    byId("goal-state").textContent = number.format(goal) + " km";
    byId("goal-copy").textContent =
      "已完成 " +
      percent.toFixed(1) +
      "% · 还差 " +
      number.format(Math.max(0, goal - totals.distance)) +
      " km";
    progress.hidden = false;
    progress.style.setProperty("--progress", percent + "%");
  }

  byId("goal-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const goal = Math.max(0, Number(goalInput.value || 0));
    try {
      if (goal)
        localStorage.setItem("distance-manifesto-" + year + "-goal", String(goal));
      else localStorage.removeItem("distance-manifesto-" + year + "-goal");
    } catch (_) {
      // File previews or privacy modes may block localStorage; the UI still updates.
    }
    renderGoal(goal);
  });

  function decodePolyline(encoded) {
    let index = 0;
    let latitude = 0;
    let longitude = 0;
    const points = [];
    while (index < encoded.length) {
      let byte;
      let shift = 0;
      let result = 0;
      do {
        byte = encoded.charCodeAt(index++) - 63;
        result |= (byte & 31) << shift;
        shift += 5;
      } while (byte >= 32);
      latitude += result & 1 ? ~(result >> 1) : result >> 1;
      shift = 0;
      result = 0;
      do {
        byte = encoded.charCodeAt(index++) - 63;
        result |= (byte & 31) << shift;
        shift += 5;
      } while (byte >= 32);
      longitude += result & 1 ? ~(result >> 1) : result >> 1;
      points.push([latitude / 1e5, longitude / 1e5]);
    }
    return points;
  }

  const decodedCache = new Map();
  function routePoints(route) {
    if (!decodedCache.has(route.id)) {
      decodedCache.set(route.id, decodePolyline(route.polyline));
    }
    return decodedCache.get(route.id);
  }

  function interpolateColor(level) {
    const stops = [
      [0, [101, 30, 10]],
      [0.3, [229, 63, 18]],
      [0.68, [255, 161, 61]],
      [1, [255, 242, 211]],
    ];
    let next = stops.findIndex((stop) => level <= stop[0]);
    if (next <= 0) return stops[0][1];
    if (next < 0) return stops[stops.length - 1][1];
    const before = stops[next - 1];
    const after = stops[next];
    const progress = (level - before[0]) / (after[0] - before[0]);
    return before[1].map((value, index) =>
      Math.round(value + (after[1][index] - value) * progress),
    );
  }

  function traceRoute(context, points, project) {
    context.beginPath();
    points.forEach((point, index) => {
      const [x, y] = project(point);
      if (index) context.lineTo(x, y);
      else context.moveTo(x, y);
    });
    context.stroke();
  }

  const routeCanvas = byId("route-heatmap");
  let activeRouteMonth = "all";
  let activeRouteMode = "all";
  let activeRouteId = "";
  let mapFrame = 0;

  function filteredRoutes() {
    return routes.filter((route) => {
      if (
        activeRouteMonth !== "all" &&
        route.date.slice(5, 7) !== activeRouteMonth
      )
        return false;
      const activity = activityById.get(String(route.id));
      if (activeRouteMode === "century" && route.distance_km < 100)
        return false;
      if (
        activeRouteMode === "photos" &&
        !(activity && activity.photo_count > 0)
      )
        return false;
      if (activeRouteMode === "prs" && !(activity && activity.pr_count > 0))
        return false;
      return true;
    });
  }

  function updateMapCoordinates(minLat, maxLat, minLng, maxLng) {
    document.querySelector(".map-coordinate.nw").innerHTML =
      maxLat.toFixed(2) + " N<br>" + minLng.toFixed(2) + " E";
    document.querySelector(".map-coordinate.ne").innerHTML =
      maxLat.toFixed(2) + " N<br>" + maxLng.toFixed(2) + " E";
    document.querySelector(".map-coordinate.sw").innerHTML =
      minLat.toFixed(2) + " N<br>" + minLng.toFixed(2) + " E";
    document.querySelector(".map-coordinate.se").innerHTML =
      minLat.toFixed(2) + " N<br>" + maxLng.toFixed(2) + " E";
  }

  function drawRouteHeatmap() {
    const visibleRoutes = filteredRoutes();
    const decoded = visibleRoutes
      .map((route) => ({ route, points: routePoints(route) }))
      .filter((item) => item.points.length > 1);
    const allPoints = decoded.flatMap((item) => item.points);
    const bounds = routeCanvas.getBoundingClientRect();
    byId("route-count").textContent = visibleRoutes.length;
    byId("route-filter-label").innerHTML =
      (activeRouteMonth === "all"
        ? "ALL OUTDOOR"
        : monthNames[Number(activeRouteMonth) - 1] + " OUTDOOR") +
      "<br>" +
      activeRouteMode.toUpperCase();
    if (!bounds.width || !bounds.height || !allPoints.length) {
      const context = routeCanvas.getContext("2d");
      routeCanvas.width = Math.max(1, Math.round(bounds.width));
      routeCanvas.height = Math.max(1, Math.round(bounds.height));
      context.clearRect(0, 0, routeCanvas.width, routeCanvas.height);
      byId("route-status").textContent = "当前筛选没有可绘制的真实路线。";
      return;
    }
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.round(bounds.width * dpr);
    const height = Math.round(bounds.height * dpr);
    const latitudes = allPoints.map((point) => point[0]);
    const longitudes = allPoints.map((point) => point[1]);
    const minLat = Math.min(...latitudes);
    const maxLat = Math.max(...latitudes);
    const minLng = Math.min(...longitudes);
    const maxLng = Math.max(...longitudes);
    updateMapCoordinates(minLat, maxLat, minLng, maxLng);
    const longitudeFactor = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);
    const minX = minLng * longitudeFactor;
    const maxX = maxLng * longitudeFactor;
    const mapWidth = maxX - minX || 1;
    const mapHeight = maxLat - minLat || 1;
    const padding = 27 * dpr;
    const scale = Math.min(
      (width - padding * 2) / mapWidth,
      (height - padding * 2) / mapHeight,
    );
    const offsetX = (width - mapWidth * scale) / 2;
    const offsetY = (height - mapHeight * scale) / 2;
    const project = ([latitude, longitude]) => [
      offsetX + (longitude * longitudeFactor - minX) * scale,
      height - (offsetY + (latitude - minLat) * scale),
    ];
    const densityCanvas = document.createElement("canvas");
    const colorCanvas = document.createElement("canvas");
    routeCanvas.width = densityCanvas.width = colorCanvas.width = width;
    routeCanvas.height = densityCanvas.height = colorCanvas.height = height;
    const densityContext = densityCanvas.getContext("2d", {
      willReadFrequently: true,
    });
    densityContext.globalCompositeOperation = "lighter";
    densityContext.strokeStyle = "rgba(255,255,255,.055)";
    densityContext.lineWidth = 1.35 * dpr;
    densityContext.lineCap = "round";
    densityContext.lineJoin = "round";
    decoded.forEach(({ points }) =>
      traceRoute(densityContext, points, project),
    );
    const densityPixels = densityContext.getImageData(0, 0, width, height);
    const colorContext = colorCanvas.getContext("2d");
    const colorPixels = colorContext.createImageData(width, height);
    for (let index = 0; index < densityPixels.data.length; index += 4) {
      const density = densityPixels.data[index + 3] / 255;
      if (!density) continue;
      const level = Math.min(1, Math.pow(density / 0.62, 0.55));
      const [red, green, blue] = interpolateColor(level);
      colorPixels.data[index] = red;
      colorPixels.data[index + 1] = green;
      colorPixels.data[index + 2] = blue;
      colorPixels.data[index + 3] = Math.round(92 + level * 163);
    }
    colorContext.putImageData(colorPixels, 0, 0);
    const context = routeCanvas.getContext("2d");
    context.clearRect(0, 0, width, height);
    context.save();
    context.globalAlpha = 0.38;
    context.filter = "blur(" + 3 * dpr + "px)";
    context.drawImage(colorCanvas, 0, 0);
    context.restore();
    context.drawImage(colorCanvas, 0, 0);
    const selected = decoded.find(
      ({ route }) => String(route.id) === activeRouteId,
    );
    if (selected) {
      context.save();
      context.strokeStyle = "#fff2d8";
      context.lineWidth = 2.6 * dpr;
      context.lineCap = "round";
      context.lineJoin = "round";
      context.shadowColor = "#ff8b45";
      context.shadowBlur = 8 * dpr;
      traceRoute(context, selected.points, project);
      context.restore();
    }
    byId("route-status").textContent =
      visibleRoutes.length.toLocaleString("zh-CN") +
      " ROUTES / " +
      allPoints.length.toLocaleString("zh-CN") +
      " POINTS" +
      (selected ? " / HIGHLIGHTED" : " / TRUE GPS TRACES");
  }

  function scheduleRouteMap() {
    cancelAnimationFrame(mapFrame);
    mapFrame = requestAnimationFrame(drawRouteHeatmap);
  }

  function renderRouteFocus() {
    const visible = filteredRoutes()
      .sort((a, b) => b.distance_km - a.distance_km)
      .slice(0, 4);
    if (
      activeRouteId &&
      !filteredRoutes().some((route) => String(route.id) === activeRouteId)
    )
      activeRouteId = "";
    byId("route-focus-list").innerHTML = visible.length
      ? visible
          .map(
            (route, index) =>
              '<button class="route-focus" type="button" data-route-id="' +
              route.id +
              '" aria-pressed="' +
              String(String(route.id) === activeRouteId) +
              '"><i>' +
              String(index + 1).padStart(2, "0") +
              "</i><span><b>" +
              escapeHtml(route.name) +
              "</b><span>" +
              dateLabel(route.date) +
              "</span></span><strong>" +
              number.format(route.distance_km) +
              " km</strong></button>",
          )
          .join("")
      : '<p class="intro">当前筛选没有可用路线。</p>';
    byId("route-focus-list")
      .querySelectorAll("[data-route-id]")
      .forEach((button) => {
        button.addEventListener("click", () => {
          activeRouteId =
            button.dataset.routeId === activeRouteId
              ? ""
              : button.dataset.routeId;
          renderRouteFocus();
          scheduleRouteMap();
        });
      });
  }

  function initializeRouteFilters() {
    const months = [
      ...new Set(routes.map((route) => route.date.slice(5, 7))),
    ].sort();
    byId("route-months").innerHTML = ["all", ...months]
      .map(
        (month) =>
          '<button type="button" data-route-month="' +
          month +
          '" aria-pressed="' +
          String(month === "all") +
          '">' +
          (month === "all" ? "全年" : month) +
          "</button>",
      )
      .join("");
    byId("route-months")
      .querySelectorAll("[data-route-month]")
      .forEach((button) => {
        button.addEventListener("click", () => {
          activeRouteMonth = button.dataset.routeMonth;
          byId("route-months")
            .querySelectorAll("[data-route-month]")
            .forEach((item) =>
              item.setAttribute("aria-pressed", String(item === button)),
            );
          activeRouteId = "";
          renderRouteFocus();
          scheduleRouteMap();
        });
      });
    byId("route-mode").addEventListener("change", (event) => {
      activeRouteMode = event.target.value;
      activeRouteId = "";
      renderRouteFocus();
      scheduleRouteMap();
    });
    byId("clear-route").addEventListener("click", () => {
      activeRouteId = "";
      renderRouteFocus();
      scheduleRouteMap();
    });
    renderRouteFocus();
  }

  let activityVisible = 8;
  function filteredActivities() {
    const query = byId("activity-search").value.trim().toLowerCase();
    const selectedMonth = byId("activity-month").value;
    const sort = byId("activity-sort").value;
    const result = activities.filter((activity) => {
      if (
        selectedMonth !== "all" &&
        activity.date.slice(5, 7) !== selectedMonth
      )
        return false;
      if (query && !activity.name.toLowerCase().includes(query)) return false;
      return true;
    });
    const sorters = {
      date: (a, b) => b.date.localeCompare(a.date),
      distance: (a, b) => b.distance_km - a.distance_km,
      elevation: (a, b) => b.elev_m - a.elev_m,
      speed: (a, b) => b.avg_speed_kmh - a.avg_speed_kmh,
      kudos: (a, b) => b.kudos - a.kudos,
      prs: (a, b) => b.pr_count - a.pr_count,
    };
    return result.sort(sorters[sort]);
  }

  function activityBadges(activity) {
    const badges = [];
    if (activity.pr_count) badges.push("PR ×" + activity.pr_count);
    if (activity.photo_count) badges.push("PHOTO ×" + activity.photo_count);
    if (activity.sport_type === "VirtualRide") badges.push("VIRTUAL");
    return badges.map((badge) => "<i>" + badge + "</i>").join("");
  }

  function renderActivityList() {
    const result = filteredActivities();
    const shown = result.slice(0, activityVisible);
    byId("activity-result-count").textContent = result.length + " 条结果";
    byId("activity-list").innerHTML = shown
      .map(
        (activity) =>
          '<button class="activity-row" type="button" data-activity-id="' +
          activity.id +
          '"><time>' +
          activity.date.slice(5).replace("-", "/") +
          "</time><span><h3>" +
          escapeHtml(activity.name) +
          '</h3><span class="activity-row-meta"><span>' +
          number.format(activity.distance_km) +
          " km</span><span>" +
          integer.format(activity.elev_m) +
          " m</span><span>" +
          number.format(activity.avg_speed_kmh) +
          ' km/h</span></span><span class="activity-badges">' +
          activityBadges(activity) +
          "</span></span></button>",
      )
      .join("");
    byId("load-more").hidden = shown.length >= result.length;
    byId("activity-list")
      .querySelectorAll("[data-activity-id]")
      .forEach((button) =>
        button.addEventListener("click", () =>
          openActivityDetail(button.dataset.activityId),
        ),
      );
  }

  function initializeActivityFilters() {
    const months = [
      ...new Set(activities.map((activity) => activity.date.slice(5, 7))),
    ].sort();
    byId("activity-month").insertAdjacentHTML(
      "beforeend",
      months
        .map(
          (month) =>
            '<option value="' + month + '">' + Number(month) + "月</option>",
        )
        .join(""),
    );
    ["activity-search", "activity-month", "activity-sort"].forEach((id) => {
      byId(id).addEventListener(
        id === "activity-search" ? "input" : "change",
        () => {
          activityVisible = 8;
          renderActivityList();
        },
      );
    });
    byId("load-more").addEventListener("click", () => {
      activityVisible += 8;
      renderActivityList();
    });
    renderActivityList();
  }

  const detailDialog = byId("activity-detail");
  function drawSingleRoute(activity) {
    const canvas = byId("detail-route");
    const bounds = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.round(bounds.width * dpr));
    const height = Math.max(1, Math.round(bounds.height * dpr));
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    context.clearRect(0, 0, width, height);
    if (!activity.polyline) {
      context.fillStyle = "#98877a";
      context.font = 12 * dpr + "px Menlo";
      context.textAlign = "center";
      context.fillText("NO GPS TRACE", width / 2, height / 2);
      return;
    }
    const points = decodePolyline(activity.polyline);
    const latitudes = points.map((point) => point[0]);
    const longitudes = points.map((point) => point[1]);
    const minLat = Math.min(...latitudes);
    const maxLat = Math.max(...latitudes);
    const minLng = Math.min(...longitudes);
    const maxLng = Math.max(...longitudes);
    const longitudeFactor = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);
    const minX = minLng * longitudeFactor;
    const maxX = maxLng * longitudeFactor;
    const spanX = maxX - minX || 1;
    const spanY = maxLat - minLat || 1;
    const padding = 24 * dpr;
    const scale = Math.min(
      (width - padding * 2) / spanX,
      (height - padding * 2) / spanY,
    );
    const offsetX = (width - spanX * scale) / 2;
    const offsetY = (height - spanY * scale) / 2;
    const project = ([latitude, longitude]) => [
      offsetX + (longitude * longitudeFactor - minX) * scale,
      height - (offsetY + (latitude - minLat) * scale),
    ];
    context.strokeStyle = "#f05523";
    context.lineWidth = 2 * dpr;
    context.lineCap = "round";
    context.lineJoin = "round";
    context.shadowColor = "#f05523";
    context.shadowBlur = 7 * dpr;
    traceRoute(context, points, project);
  }

  function openActivityDetail(id) {
    const activity = activityById.get(String(id));
    if (!activity) return;
    byId("detail-name").textContent = activity.name;
    byId("detail-date").textContent =
      activity.date + " / " + activity.sport_type;
    const tags = [];
    if (activity.pr_count) tags.push(activity.pr_count + " PR");
    if (activity.photo_count) tags.push(activity.photo_count + " PHOTOS");
    if (activity.athletes > 1) tags.push(activity.athletes + " ATHLETES");
    byId("detail-tags").innerHTML = tags
      .map((tag) => "<span>" + tag + "</span>")
      .join("");
    const metrics = [
      ["距离", number.format(activity.distance_km) + " km"],
      ["爬升", integer.format(activity.elev_m) + " m"],
      ["移动时间", hours(activity.moving_seconds).toFixed(1) + " h"],
      ["平均速度", number.format(activity.avg_speed_kmh) + " km/h"],
      ["kudos", integer.format(activity.kudos)],
      ["成就", integer.format(activity.achievements)],
    ];
    byId("detail-metrics").innerHTML = metrics
      .map(
        ([label, value]) =>
          "<div><span>" + label + "</span><b>" + value + "</b></div>",
      )
      .join("");
    byId("detail-strava").href =
      "https://www.strava.com/activities/" + activity.id;
    if (typeof detailDialog.showModal === "function") detailDialog.showModal();
    else detailDialog.setAttribute("open", "");
    requestAnimationFrame(() => drawSingleRoute(activity));
  }

  byId("close-detail").addEventListener("click", () => detailDialog.close());

  function initializeMenu() {
    const toggle = byId("menu-toggle");
    const nav = byId("section-nav");
    function setMenu(open) {
      nav.hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
      document.body.classList.toggle("nav-open", open);
    }
    toggle.addEventListener("click", () => setMenu(nav.hidden));
    nav
      .querySelectorAll("a")
      .forEach((link) => link.addEventListener("click", () => setMenu(false)));
  }

  function initializeAlbum() {
    const viewer = byId("album-viewer");
    const openAlbum = byId("open-album");
    const closeAlbum = byId("close-album");
    let returnFocus = null;
    function setAlbum(open) {
      viewer.hidden = !open;
      document.body.classList.toggle("viewer-open", open);
      if (open) {
        returnFocus = document.activeElement;
        closeAlbum.focus();
      } else if (returnFocus) returnFocus.focus();
    }
    openAlbum.addEventListener("click", () => setAlbum(true));
    closeAlbum.addEventListener("click", () => setAlbum(false));
    viewer.addEventListener("click", (event) => {
      if (event.target === viewer) setAlbum(false);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !viewer.hidden) setAlbum(false);
    });
  }

  function renderDataHealth() {
    byId("strava-health").textContent = activities.length + " 条已缓存";
    const intervalsReady = Boolean(metrics.intervals_available);
    byId("intervals-health").textContent = intervalsReady ? "训练缓存可用" : "未配置或暂不可用";
    byId("intervals-health-dot").classList.toggle("ok", intervalsReady);
    const gear = Array.isArray(metrics.gear) ? metrics.gear : [];
    byId("gear-health").textContent = gear.length ? gear.length + " 件已同步" : "暂无装备缓存";
    byId("gear-health-dot").classList.toggle("ok", gear.length > 0);
  }

  function drawSeries(canvas, series) {
    const bounds = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.round(bounds.width * dpr));
    const height = Math.max(1, Math.round(bounds.height * dpr));
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    context.clearRect(0, 0, width, height);
    const values = series.flatMap((item) => item.values).filter(Number.isFinite);
    if (!values.length) return false;
    const minimum = Math.min(...values);
    const maximum = Math.max(...values);
    const span = maximum - minimum || 1;
    const padding = 8 * dpr;
    context.strokeStyle = "rgba(170,153,140,.18)";
    context.lineWidth = dpr;
    for (let row = 1; row < 4; row += 1) {
      const y = padding + ((height - padding * 2) * row) / 4;
      context.beginPath();
      context.moveTo(0, y);
      context.lineTo(width, y);
      context.stroke();
    }
    series.forEach((item) => {
      if (!item.values.length) return;
      context.beginPath();
      context.strokeStyle = item.color;
      context.lineWidth = (item.width || 1.6) * dpr;
      context.lineJoin = "round";
      context.lineCap = "round";
      item.values.forEach((value, index) => {
        const x = padding + ((width - padding * 2) * index) / Math.max(1, item.values.length - 1);
        const y = height - padding - ((value - minimum) / span) * (height - padding * 2);
        if (index) context.lineTo(x, y);
        else context.moveTo(x, y);
      });
      context.stroke();
    });
    return true;
  }

  function powerCurvePoints(raw, depth = 0) {
    if (!raw || depth > 3) return [];
    if (Array.isArray(raw)) {
      const points = raw
        .map((item) => ({
          seconds: Number(item.secs ?? item.seconds ?? item.duration ?? 0),
          watts: Number(item.watts ?? item.power ?? item.value ?? 0),
        }))
        .filter((item) => item.seconds > 0 && item.watts > 0);
      if (points.length) return points.sort((a, b) => a.seconds - b.seconds);
      for (const item of raw) {
        const nested = powerCurvePoints(item, depth + 1);
        if (nested.length) return nested;
      }
      return [];
    }
    if (typeof raw === "object") {
      for (const key of ["list", "power_curve", "powerCurve", "curves", "data"]) {
        const nested = powerCurvePoints(raw[key], depth + 1);
        if (nested.length) return nested;
      }
      for (const value of Object.values(raw)) {
        const nested = powerCurvePoints(value, depth + 1);
        if (nested.length) return nested;
      }
    }
    return [];
  }

  function renderGear() {
    const gear = Array.isArray(metrics.gear) ? metrics.gear : [];
    if (!gear.length) {
      byId("gear-title").textContent = "尚未同步车辆与部件。";
      byId("gear-copy").textContent = "配置 Intervals.icu 后，这里显示已同步装备的累计里程；没有缓存时不推测维护状态。";
      byId("gear-list").innerHTML = "";
      return;
    }
    byId("gear-title").textContent = gear.length + " 件装备已同步。";
    byId("gear-copy").textContent = "以下为 Intervals.icu 返回的累计里程；维护阈值未配置，因此不生成保养结论。";
    byId("gear-list").innerHTML = gear
      .map((item) => '<div class="gear-item"><span>' + escapeHtml(item.name || "未命名装备") + '</span><strong>' + number.format(Number(item.distance_km || 0)) + " km</strong></div>")
      .join("");
  }

  function renderTraining() {
    const load = Array.isArray(metrics.training_load) ? metrics.training_load : [];
    const ftp = Array.isArray(metrics.ftp_trend) ? metrics.ftp_trend : [];
    const intervalsReady = Boolean(metrics.intervals_available);
    byId("training-status-dot").classList.toggle("ok", intervalsReady);
    byId("training-status-copy").textContent = intervalsReady
      ? "Intervals.icu 训练缓存已接入"
      : "Intervals.icu 未配置或同步失败";
    byId("training-intro").textContent = intervalsReady
      ? "训练曲线来自构建时同步的 Intervals.icu 缓存，并由确定性规则计算；页面不接触 API 密钥。"
      : "当前没有 Intervals.icu 缓存。训练区块保留完整信息架构，但不生成 CTL、ATL、TSB、FTP 或功率假数据。";

    const loadCanvas = byId("training-load-chart");
    const recentLoad = load.slice(-120);
    loadCanvas.hidden = !recentLoad.length;
    if (recentLoad.length) {
      const latest = recentLoad[recentLoad.length - 1];
      byId("training-load-copy").textContent =
        "CTL " + number.format(latest.ctl) + " · ATL " + number.format(latest.atl) + " · TSB " + number.format(latest.tsb);
      drawSeries(loadCanvas, [
        { values: recentLoad.map((item) => Number(item.ctl)), color: "#f4e8d8", width: 2 },
        { values: recentLoad.map((item) => Number(item.atl)), color: "#f05523", width: 1.7 },
        { values: recentLoad.map((item) => Number(item.tsb)), color: "#a78bfa", width: 1.2 },
      ]);
    } else {
      byId("training-load-copy").textContent = "没有负荷记录，不绘制曲线。";
    }

    const ftpCanvas = byId("ftp-chart");
    ftpCanvas.hidden = !ftp.length;
    if (ftp.length) {
      const latest = ftp[ftp.length - 1];
      byId("ftp-copy").textContent = "最新 FTP " + integer.format(latest.ftp) + " W · " + latest.date;
      drawSeries(ftpCanvas, [{ values: ftp.map((item) => Number(item.ftp)), color: "#f05523", width: 2.2 }]);
    } else {
      byId("ftp-copy").textContent = "缓存中没有 FTP 记录。";
    }

    const power = powerCurvePoints(metrics.power_curve);
    const powerCanvas = byId("power-chart");
    powerCanvas.hidden = !power.length;
    if (power.length) {
      byId("power-copy").textContent = power.length + " 个持续时间点 · 峰值 " + integer.format(Math.max(...power.map((item) => item.watts))) + " W";
      drawSeries(powerCanvas, [{ values: power.map((item) => item.watts), color: "#f4e8d8", width: 2 }]);
    } else {
      byId("power-copy").textContent = "缓存中没有可识别的功率曲线。";
    }
  }

  function renderSeason() {
    const season = metrics.season || {};
    let days = Number(season.days);
    if (!Number.isFinite(days)) {
      const start = Date.UTC(2027, 3, 1);
      const now = new Date();
      days = Math.max(0, Math.ceil((start - Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())) / 86400000));
    }
    byId("season-days").textContent = days;
    byId("season-weeks").textContent = "天 / " + (season.weeks ?? Math.floor(days / 7)) + " 周";
  }

  renderHero();
  renderRecent();
  renderRhythm();
  renderCalendar();
  renderRecords();
  renderGoal(readGoal());
  renderDataHealth();
  renderGear();
  renderTraining();
  initializeRouteFilters();
  initializeActivityFilters();
  initializeMenu();
  initializeAlbum();
  renderSeason();
  if ("ResizeObserver" in window) {
    new ResizeObserver(scheduleRouteMap).observe(routeCanvas);
  } else {
    window.addEventListener("resize", scheduleRouteMap);
  }
  scheduleRouteMap();
  dataStatus.dataset.state = "ready";
})();
