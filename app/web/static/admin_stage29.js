(() => {
  const canvases = new WeakMap();

  function css(name, fallback) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
  }

  function prepare(canvas) {
    const ratio = devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    return {ctx, width: rect.width, height: rect.height};
  }

  function updateInfo(canvas, row) {
    const panel = canvas.closest(".panel");
    const info = panel?.querySelector("[data-chart-info]");
    if (!info || !row) return;
    info.innerHTML =
      "<strong>" + row.label + "</strong>" +
      "<span>Новые: " + (row.users || 0) +
      " · Заблокировали: " + (row.blocked || 0) +
      " · Сообщения: " + (row.questions || 0) +
      " · Ответы: " + (row.answers || 0) +
      " · Доход: " + Number(row.revenue || 0).toLocaleString("ru-RU") + " ₽</span>";
  }

  function draw(canvas, data, selectedOverride) {
    if (!canvas || !data.length) return;

    const {ctx, width, height} = prepare(canvas);
    const pad = {left: 38, right: 16, top: 18, bottom: 34};
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;
    const series = [
      ["users", css("--purple", "#8b7cff")],
      ["blocked", css("--red", "#ff7185")],
      ["questions", css("--cyan", "#55d8ff")],
      ["answers", css("--green", "#52d3a7")],
    ];
    const max = Math.max(
      1,
      ...data.flatMap((row) => series.map(([key]) => Number(row[key] || 0)))
    );

    const old = canvases.get(canvas);
    const selected = selectedOverride ?? old?.selected ?? -1;
    const state = {data, selected, x: []};
    canvases.set(canvas, state);

    const x = (index) =>
      pad.left + (data.length === 1 ? 0 : innerW * index / (data.length - 1));
    const y = (value) =>
      pad.top + innerH - Number(value || 0) / max * innerH;
    state.x = data.map((_, index) => x(index));

    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = css("--line", "#293854");
    ctx.fillStyle = css("--muted", "#93a1bd");
    ctx.font = "11px system-ui";

    for (let index = 0; index <= 4; index++) {
      const yy = pad.top + innerH * index / 4;
      ctx.beginPath();
      ctx.moveTo(pad.left, yy);
      ctx.lineTo(width - pad.right, yy);
      ctx.stroke();
      ctx.fillText(String(Math.round(max * (1 - index / 4))), 4, yy + 4);
    }

    if (selected >= 0) {
      ctx.fillStyle = css("--surface-3", "#1d2b46");
      ctx.fillRect(x(selected) - 18, pad.top, 36, innerH);
    }

    series.forEach(([key, color]) => {
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.4;
      data.forEach((row, index) => {
        if (index === 0) ctx.moveTo(x(index), y(row[key]));
        else ctx.lineTo(x(index), y(row[key]));
      });
      ctx.stroke();

      data.forEach((row, index) => {
        ctx.beginPath();
        ctx.fillStyle = color;
        ctx.arc(x(index), y(row[key]), selected === index ? 5 : 3, 0, Math.PI * 2);
        ctx.fill();
      });
    });

    const every = Math.max(1, Math.ceil(data.length / 7));
    data.forEach((row, index) => {
      if (index % every === 0 || index === data.length - 1) {
        ctx.fillText(row.label, x(index) - 13, height - 9);
      }
    });

    canvas.style.cursor = "pointer";
  }

  function nearestPoint(canvas, event) {
    const state = canvases.get(canvas);
    if (!state) return -1;
    const clickX = event.clientX - canvas.getBoundingClientRect().left;
    let best = 0;
    let distance = Infinity;
    state.x.forEach((candidate, index) => {
      const current = Math.abs(candidate - clickX);
      if (current < distance) {
        distance = current;
        best = index;
      }
    });
    return best;
  }

  document.querySelectorAll("canvas[data-chart]:not([data-stage294-chart])").forEach((canvas) => {
    let data = [];
    try {
      data = JSON.parse(canvas.dataset.chart || "[]");
    } catch {
      return;
    }

    draw(canvas, data);

    canvas.addEventListener("pointerup", (event) => {
      const index = nearestPoint(canvas, event);
      if (index < 0) return;
      draw(canvas, data, index);
      updateInfo(canvas, data[index]);
    });
  });

  document.querySelectorAll("[data-chart-range] button").forEach((button) => {
    button.addEventListener("click", async () => {
      document.querySelectorAll("[data-chart-range] button").forEach((item) => {
        item.classList.toggle("active", item === button);
      });

      const response = await fetch(
        "/admin/business/api/chart?days=" + button.dataset.days
      );
      if (!response.ok) return;

      const payload = await response.json();
      const canvas = document.getElementById("businessChart");
      if (!canvas) return;

      const data = payload.items || [];
      canvas.dataset.chart = JSON.stringify(data);
      draw(canvas, data);
      const info = canvas.closest(".panel")?.querySelector("[data-chart-info]");
      if (info) {
        info.innerHTML =
          "<strong>Выберите точку</strong>" +
          "<span>Нажмите на день на графике, чтобы увидеть показатели.</span>";
      }
    });
  });

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      await navigator.clipboard.writeText(button.dataset.copy || "");
      const original = button.textContent;
      button.textContent = "Скопировано";
      setTimeout(() => { button.textContent = original; }, 1400);
    });
  });

  const modal = document.querySelector("[data-confirm-modal]");
  document.querySelectorAll("[data-confirm-open]").forEach((button) => {
    button.addEventListener("click", () => { if (modal) modal.hidden = false; });
  });
  document.querySelectorAll("[data-confirm-close]").forEach((button) => {
    button.addEventListener("click", () => { if (modal) modal.hidden = true; });
  });

  const preview = document.querySelector(".broadcast-preview em");
  const textarea = document.querySelector('textarea[name="text"]');
  textarea?.addEventListener("input", () => {
    if (preview) preview.textContent = textarea.value || "Текст появится здесь";
  });

  const currentPath = window.location.pathname.replace(/\/$/, "");
  document.querySelectorAll(".pro-nav a").forEach((link) => {
    const path = new URL(link.href, window.location.origin).pathname.replace(/\/$/, "");
    const isActive =
      path === currentPath ||
      (path !== "/admin/business" && currentPath.startsWith(path + "/"));
    link.classList.toggle("active", isActive);
  });
})();
