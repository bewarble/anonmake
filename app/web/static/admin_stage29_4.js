(() => {
  const state = new WeakMap();

  function color(name, fallback) {
    return getComputedStyle(document.documentElement)
      .getPropertyValue(name).trim() || fallback;
  }

  function prepare(canvas) {
    const ratio = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    return {ctx, width: rect.width, height: rect.height};
  }

  function draw(canvas, data, selected = -1) {
    if (!data.length) return;

    const {ctx, width, height} = prepare(canvas);
    const pad = {left: 40, right: 18, top: 18, bottom: 34};
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;

    const lineSeries = [
      ["users", color("--purple", "#8b7cff")],
      ["questions", color("--cyan", "#55d8ff")],
      ["answers", color("--green", "#52d3a7")],
    ];

    const max = Math.max(
      1,
      ...data.flatMap(row => [
        Number(row.users || 0),
        Number(row.blocked || 0),
        Number(row.questions || 0),
        Number(row.answers || 0),
      ])
    );

    const x = index =>
      pad.left + (data.length === 1 ? innerW / 2 : innerW * index / (data.length - 1));
    const y = value =>
      pad.top + innerH - Number(value || 0) / max * innerH;

    const xPositions = data.map((_, index) => x(index));
    state.set(canvas, {data, selected, xPositions});

    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = color("--line", "#293854");
    ctx.fillStyle = color("--muted", "#93a1bd");
    ctx.font = "11px system-ui";
    ctx.lineWidth = 1;

    for (let index = 0; index <= 4; index++) {
      const yy = pad.top + innerH * index / 4;
      ctx.beginPath();
      ctx.moveTo(pad.left, yy);
      ctx.lineTo(width - pad.right, yy);
      ctx.stroke();
      ctx.fillText(String(Math.round(max * (1 - index / 4))), 4, yy + 4);
    }

    if (selected >= 0) {
      ctx.fillStyle = color("--surface-3", "#1d2b46");
      ctx.fillRect(x(selected) - 18, pad.top, 36, innerH);
    }

    // Red blocked metric is rendered as columns, so it cannot disappear
    // underneath zero-value lines.
    const red = color("--red", "#ff7185");
    const barWidth = Math.max(4, Math.min(11, innerW / Math.max(data.length, 1) * .36));
    data.forEach((row, index) => {
      const value = Number(row.blocked || 0);
      const top = y(value);
      const bottom = pad.top + innerH;
      ctx.fillStyle = value > 0 ? red : "rgba(255,113,133,.18)";
      ctx.fillRect(x(index) - barWidth / 2, value > 0 ? top : bottom - 2, barWidth, value > 0 ? bottom - top : 2);
    });

    lineSeries.forEach(([key, seriesColor]) => {
      ctx.beginPath();
      ctx.strokeStyle = seriesColor;
      ctx.lineWidth = 2.5;
      data.forEach((row, index) => {
        if (index === 0) ctx.moveTo(x(index), y(row[key]));
        else ctx.lineTo(x(index), y(row[key]));
      });
      ctx.stroke();

      data.forEach((row, index) => {
        ctx.beginPath();
        ctx.fillStyle = seriesColor;
        ctx.arc(x(index), y(row[key]), selected === index ? 5 : 3, 0, Math.PI * 2);
        ctx.fill();
      });
    });

    const every = Math.max(1, Math.ceil(data.length / 7));
    data.forEach((row, index) => {
      if (index % every === 0 || index === data.length - 1) {
        ctx.fillStyle = color("--muted", "#93a1bd");
        ctx.fillText(row.label, x(index) - 13, height - 9);
      }
    });

    canvas.style.cursor = "pointer";
  }

  function updateInfo(canvas, row) {
    const info = canvas.closest(".panel")?.querySelector("[data-chart-info]");
    if (!info) return;
    info.innerHTML =
      `<strong>${row.label}</strong>` +
      `<span>Новые: ${row.users || 0} · ` +
      `Заблокировали: ${row.blocked || 0} · ` +
      `Сообщения: ${row.questions || 0} · ` +
      `Ответы: ${row.answers || 0} · ` +
      `Доход: ${Number(row.revenue || 0).toLocaleString("ru-RU")} ₽</span>`;
    info.classList.add("selected");
  }

  function bind(canvas) {
    let data;
    try {
      data = JSON.parse(canvas.dataset.chart || "[]");
    } catch {
      return;
    }

    draw(canvas, data);

    canvas.addEventListener("pointerup", event => {
      const current = state.get(canvas);
      if (!current || !current.data.length) return;

      const clickX = event.clientX - canvas.getBoundingClientRect().left;
      let selected = 0;
      let distance = Infinity;

      current.xPositions.forEach((candidate, index) => {
        const currentDistance = Math.abs(candidate - clickX);
        if (currentDistance < distance) {
          distance = currentDistance;
          selected = index;
        }
      });

      draw(canvas, current.data, selected);
      updateInfo(canvas, current.data[selected]);
    });
  }

  function init() {
    document.querySelectorAll("[data-stage294-chart]").forEach(bind);
  }

  document.addEventListener("DOMContentLoaded", init);
  window.addEventListener("pageshow", init);
})();
