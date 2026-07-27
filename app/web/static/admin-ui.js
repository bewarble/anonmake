/* AnonMake Admin UI — consolidated in Stage 35. */
"use strict";

/* ===== legacy source: admin_stage28.js ===== */

(() => {
  const root = document.documentElement;
  const storedTheme = localStorage.getItem("anonmake-theme");
  if (storedTheme) root.dataset.theme = storedTheme;

  const sidebar = document.querySelector("[data-sidebar]");
  let backdrop = document.querySelector("[data-sidebar-backdrop]");
  if (!backdrop) {
    backdrop = document.createElement("div");
    backdrop.className = "sidebar-backdrop";
    backdrop.dataset.sidebarBackdrop = "";
    document.body.appendChild(backdrop);
  }

  const setSidebar = (open) => {
    sidebar?.classList.toggle("open", open);
    backdrop?.classList.toggle("open", open);
    document.body.style.overflow = open ? "hidden" : "";
  };

  document.querySelectorAll("[data-sidebar-toggle]").forEach((button) => {
    button.addEventListener("click", () => setSidebar(!sidebar?.classList.contains("open")));
  });
  document.querySelectorAll("[data-sidebar-close]").forEach((button) => {
    button.addEventListener("click", () => setSidebar(false));
  });
  backdrop?.addEventListener("click", () => setSidebar(false));
  document.querySelectorAll(".pro-nav a").forEach((link) => {
    link.addEventListener("click", () => {
      if (window.innerWidth <= 760) setSidebar(false);
    });
  });

  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const next = root.dataset.theme === "light" ? "dark" : "light";
      root.dataset.theme = next;
      localStorage.setItem("anonmake-theme", next);
      renderAllCharts();
    });
  });

  const overlay = document.querySelector("[data-command-overlay]");
  const commandInput = document.querySelector("[data-command-input]");
  const openCommand = () => {
    if (!overlay) return;
    overlay.hidden = false;
    setTimeout(() => commandInput?.focus(), 0);
  };
  const closeCommand = () => { if (overlay) overlay.hidden = true; };

  document.querySelectorAll("[data-command-open]").forEach((button) => button.addEventListener("click", openCommand));
  overlay?.addEventListener("click", (event) => { if (event.target === overlay) closeCommand(); });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault(); openCommand();
    }
    if (event.key === "Escape") { closeCommand(); setSidebar(false); }
  });

  const chartState = new WeakMap();

  function colors() {
    const s = getComputedStyle(root);
    return {
      text: s.getPropertyValue("--muted").trim() || "#8f9dbc",
      line: s.getPropertyValue("--line").trim() || "#263552",
      surface: s.getPropertyValue("--surface-2").trim() || "#172238",
      purple: s.getPropertyValue("--purple").trim() || "#8b7cff",
      cyan: s.getPropertyValue("--cyan").trim() || "#55d8ff",
      green: s.getPropertyValue("--green").trim() || "#52d3a7",
    };
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

  function parseData(canvas) {
    try { return JSON.parse(canvas.dataset.chart || "[]"); } catch { return []; }
  }

  function draw(canvas, data) {
    if (!data.length) return;
    const {ctx, width, height} = prepare(canvas);
    const c = colors();
    const pad = {left:36,right:16,top:18,bottom:32};
    const innerW = width-pad.left-pad.right;
    const innerH = height-pad.top-pad.bottom;
    const series = [
      {key:"users",color:c.purple,label:"Пользователи"},
      {key:"questions",color:c.cyan,label:"Сообщения"},
      {key:"answers",color:c.green,label:"Ответы"},
    ];
    const max = Math.max(1,...data.flatMap(row => series.map(s => Number(row[s.key]||0))));
    const previous = chartState.get(canvas);
    const state = {data, selected: previous?.selected ?? -1, x:[]};
    chartState.set(canvas,state);

    ctx.clearRect(0,0,width,height);
    ctx.strokeStyle=c.line; ctx.fillStyle=c.text; ctx.font="11px system-ui";
    for(let i=0;i<=4;i++){
      const y=pad.top+(innerH/4)*i;
      ctx.beginPath(); ctx.moveTo(pad.left,y); ctx.lineTo(width-pad.right,y); ctx.stroke();
      ctx.fillText(String(Math.round(max*(1-i/4))),3,y+4);
    }
    const xFor=i=>pad.left+(data.length===1?0:(innerW*i)/(data.length-1));
    const yFor=v=>pad.top+innerH-(Number(v||0)/max)*innerH;
    state.x=data.map((_,i)=>xFor(i));

    if(state.selected>=0){
      const x=xFor(state.selected);
      ctx.fillStyle=c.surface; ctx.fillRect(x-18,pad.top,36,innerH);
    }

    series.forEach(s=>{
      ctx.beginPath(); ctx.strokeStyle=s.color; ctx.lineWidth=2.5;
      data.forEach((row,i)=> i===0?ctx.moveTo(xFor(i),yFor(row[s.key])):ctx.lineTo(xFor(i),yFor(row[s.key])));
      ctx.stroke();
      data.forEach((row,i)=>{
        ctx.beginPath(); ctx.fillStyle=s.color;
        ctx.arc(xFor(i),yFor(row[s.key]),state.selected===i?5:3,0,Math.PI*2); ctx.fill();
      });
    });

    const every=Math.max(1,Math.ceil(data.length/7));
    data.forEach((row,i)=>{
      if(i%every!==0 && i!==data.length-1)return;
      ctx.fillStyle=c.text; ctx.fillText(row.label,xFor(i)-13,height-8);
    });

    canvas.style.cursor="pointer";
    canvas.onclick=(event)=>{
      const rect=canvas.getBoundingClientRect();
      const clickX=event.clientX-rect.left;
      let best=0,distance=Infinity;
      state.x.forEach((candidate,i)=>{
        const current=Math.abs(candidate-clickX);
        if(current<distance){distance=current;best=i;}
      });
      state.selected=best;
      draw(canvas,data);
      const row=data[best];
      const detail=canvas.parentElement?.querySelector("[data-chart-detail]");
      if(detail){
        detail.innerHTML="<strong>"+row.label+"</strong><br>"+
          "Пользователи: "+(row.users||0)+" · Сообщения: "+(row.questions||0)+
          " · Ответы: "+(row.answers||0)+" · Доход: "+
          Number(row.revenue||0).toLocaleString("ru-RU")+" ₽";
      }
    };
  }

  function renderAllCharts(){
    document.querySelectorAll("canvas[data-chart]:not(#businessChart)").forEach(canvas=>draw(canvas,parseData(canvas)));
  }

  let timer;
  window.addEventListener("resize",()=>{clearTimeout(timer);timer=setTimeout(renderAllCharts,120);});
  renderAllCharts();
})();


/* ===== legacy source: admin_stage29.js ===== */

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


/* ===== legacy source: admin_stage29_3.js ===== */

(() => {
  function activateNavigation() {
    const current = window.location.pathname.replace(/\/$/, "");

    document.querySelectorAll(".pro-nav a").forEach((link) => {
      const path = new URL(link.href, window.location.origin)
        .pathname.replace(/\/$/, "");

      let active = false;
      if (path === "/admin/business") {
        active = current === "/admin/business";
      } else if (path === "/admin/business/analytics") {
        active = current.startsWith("/admin/business/analytics");
      } else {
        active = current === path || current.startsWith(path + "/");
      }
      link.classList.toggle("active", active);
    });
  }

  function bindChart(canvas) {
    if (!canvas || canvas.dataset.stage293Bound === "1") return;
    canvas.dataset.stage293Bound = "1";

    let data;
    try {
      data = JSON.parse(canvas.dataset.chart || "[]");
    } catch {
      return;
    }

    canvas.addEventListener("pointerup", (event) => {
      if (!data.length) return;

      const rect = canvas.getBoundingClientRect();
      const left = 38;
      const right = 16;
      const usable = Math.max(rect.width - left - right, 1);
      const clickX = Math.min(
        Math.max(event.clientX - rect.left - left, 0),
        usable
      );
      const index = Math.min(
        Math.round(clickX / usable * (data.length - 1)),
        data.length - 1
      );
      const row = data[index];
      const info = canvas.closest(".panel")?.querySelector("[data-chart-info]");

      if (info) {
        info.innerHTML =
          `<strong>${row.label}</strong>` +
          `<span>Новые: ${row.users || 0} · ` +
          `Заблокировали: ${row.blocked || 0} · ` +
          `Сообщения: ${row.questions || 0} · ` +
          `Ответы: ${row.answers || 0} · ` +
          `Доход: ${Number(row.revenue || 0).toLocaleString("ru-RU")} ₽</span>`;
        info.classList.add("selected");
      }
    });
  }

  function init() {
    activateNavigation();
    document.querySelectorAll("canvas[data-chart]:not([data-stage294-chart])").forEach(bindChart);
  }

  document.addEventListener("DOMContentLoaded", init);
  window.addEventListener("pageshow", init);
})();


/* ===== legacy source: admin_stage29_4.js ===== */

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


/* ===== legacy source: admin_stage32_1.js ===== */

(() => {
  "use strict";

  const html = document.documentElement;
  const body = document.body;

  function all(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function closeCommandPalette() {
    const overlay = document.querySelector("[data-command-overlay]");
    if (overlay) {
      overlay.hidden = true;
      overlay.setAttribute("aria-hidden", "true");
    }
  }

  function openCommandPalette() {
    const overlay = document.querySelector("[data-command-overlay]");
    if (!overlay) return;
    overlay.hidden = false;
    overlay.setAttribute("aria-hidden", "false");
    requestAnimationFrame(() => {
      document.querySelector("[data-command-input]")?.focus();
    });
  }

  function closeSidebar() {
    const sidebar = document.querySelector("[data-sidebar]");
    const backdrop = document.querySelector("[data-sidebar-backdrop]");
    sidebar?.classList.remove("open");
    backdrop?.classList.remove("open");
    body.classList.remove("sidebar-open");
    body.style.removeProperty("overflow");
  }

  function toggleSidebar() {
    const sidebar = document.querySelector("[data-sidebar]");
    if (!sidebar) return;
    const open = !sidebar.classList.contains("open");
    sidebar.classList.toggle("open", open);
    document.querySelector("[data-sidebar-backdrop]")?.classList.toggle("open", open);
    body.classList.toggle("sidebar-open", open);
    body.style.overflow = open ? "hidden" : "";
  }

  function initOverlays() {
    // A stale overlay was the main cause of controls becoming unclickable.
    closeCommandPalette();
    closeSidebar();

    all("[data-command-open]").forEach((button) => {
      if (button.dataset.stage321Bound) return;
      button.dataset.stage321Bound = "1";
      button.addEventListener("click", openCommandPalette);
    });

    const overlay = document.querySelector("[data-command-overlay]");
    overlay?.addEventListener("click", (event) => {
      if (event.target === overlay) closeCommandPalette();
    });

    // Sidebar events are managed by admin_stage28.js.
    // Do not register a second toggle handler here: two handlers would
    // immediately open and close the sidebar on the same click.
  }

  function initNavigation() {
    const current = window.location.pathname.replace(/\/+$/, "") || "/";
    all(".pro-nav a").forEach((link) => {
      const path = new URL(link.href, location.origin).pathname.replace(/\/+$/, "");
      let active = current === path;
      if (!active && path !== "/admin/business") {
        active = current.startsWith(path + "/");
      }
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  }

  function initCommandSearch() {
    const input = document.querySelector("[data-command-input]");
    if (!input || input.dataset.stage321Bound) return;
    input.dataset.stage321Bound = "1";
    input.addEventListener("input", () => {
      const query = input.value.trim().toLocaleLowerCase("ru-RU");
      all(".command-items a").forEach((item) => {
        item.hidden = Boolean(query) &&
          !item.textContent.toLocaleLowerCase("ru-RU").includes(query);
      });
    });
  }

  async function copyText(value) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return;
    }
    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }

  function initCopyButtons() {
    all("[data-copy]").forEach((button) => {
      if (button.dataset.stage321CopyBound) return;
      button.dataset.stage321CopyBound = "1";
      button.addEventListener("click", async () => {
        try {
          await copyText(button.dataset.copy || "");
          const original = button.textContent;
          button.textContent = "✅ Скопировано";
          setTimeout(() => { button.textContent = original; }, 1400);
        } catch {
          button.textContent = "❌ Не удалось";
        }
      });
    });
  }

  function initForms() {
    all("form").forEach((form) => {
      if (form.dataset.stage321Bound) return;
      form.dataset.stage321Bound = "1";

      form.addEventListener("submit", (event) => {
        if (!form.checkValidity()) return;

        const submitter = event.submitter ||
          form.querySelector('button[type="submit"], input[type="submit"]');
        if (!submitter || submitter.dataset.allowRepeat === "true") return;
        if (submitter.dataset.submitting === "true") {
          event.preventDefault();
          return;
        }

        submitter.dataset.submitting = "true";
        submitter.setAttribute("aria-busy", "true");
        submitter.classList.add("is-loading");

        // Do not disable synchronously: disabled submitters may be omitted from
        // FormData in some browsers. Lock after the request has been queued.
        setTimeout(() => {
          submitter.disabled = true;
        }, 0);
      });
    });
  }

  function initConfirmModals() {
    const modal = document.querySelector("[data-confirm-modal]");
    if (!modal) return;

    modal.hidden = true;
    all("[data-confirm-open]").forEach((button) => {
      if (button.dataset.stage321ConfirmBound) return;
      button.dataset.stage321ConfirmBound = "1";
      button.addEventListener("click", () => {
        modal.hidden = false;
        modal.querySelector("button, input, a")?.focus();
      });
    });
    all("[data-confirm-close]").forEach((button) => {
      button.addEventListener("click", () => { modal.hidden = true; });
    });
    modal.addEventListener("click", (event) => {
      if (event.target === modal) modal.hidden = true;
    });
  }

  function initKeyboard() {
    document.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openCommandPalette();
      }
      if (event.key === "Escape") {
        closeCommandPalette();
        const modal = document.querySelector("[data-confirm-modal]");
        if (modal) modal.hidden = true;
      }
    });
  }

  function init() {
    html.classList.add("admin-js-ready");
    initOverlays();
    initNavigation();
    initCommandSearch();
    initCopyButtons();
    initForms();
    initConfirmModals();
    initKeyboard();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, {once: true});
  } else {
    init();
  }
  window.addEventListener("pageshow", () => {
    closeCommandPalette();
    closeSidebar();
    all(".is-loading").forEach((element) => {
      element.classList.remove("is-loading");
      element.removeAttribute("aria-busy");
      element.disabled = false;
      delete element.dataset.submitting;
    });
    initNavigation();
  });
})();


/* ===== legacy source: admin_stage33.js ===== */

(() => {
  "use strict";

  function preservePaginationQuery() {
    const params = new URLSearchParams(window.location.search);
    document.querySelectorAll("[data-pagination] a[data-page]").forEach((link) => {
      const next = new URLSearchParams(params);
      next.set("page", link.dataset.page || "0");
      link.href = `${window.location.pathname}?${next.toString()}`;
    });
  }

  function normalizeExternalActions() {
    document.querySelectorAll('form button[type="submit"]').forEach((button) => {
      if (!button.textContent.trim()) button.textContent = "Сохранить";
    });
  }

  function init() {
    preservePaginationQuery();
    normalizeExternalActions();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, {once:true});
  } else {
    init();
  }
  window.addEventListener("pageshow", preservePaginationQuery);
})();


/* ===== Stage 35 final interaction guards ===== */
(() => {
  "use strict";

  function setExpanded(button, expanded) {
    if (!button) return;
    button.setAttribute("aria-expanded", expanded ? "true" : "false");
  }

  function syncSidebarAria() {
    const sidebar = document.querySelector("[data-sidebar]");
    const expanded = Boolean(sidebar?.classList.contains("open"));
    document.querySelectorAll("[data-sidebar-toggle]").forEach((button) => {
      setExpanded(button, expanded);
    });
  }

  function initAccessibility() {
    document.querySelectorAll("[data-sidebar-toggle]").forEach((button) => {
      button.setAttribute("aria-controls", "admin-sidebar");
      if (!button.hasAttribute("aria-expanded")) {
        button.setAttribute("aria-expanded", "false");
      }
    });

    const sidebar = document.querySelector("[data-sidebar]");
    if (sidebar) sidebar.id = "admin-sidebar";

    const observer = sidebar
      ? new MutationObserver(syncSidebarAria)
      : null;
    observer?.observe(sidebar, {attributes: true, attributeFilter: ["class"]});

    document.querySelectorAll("[data-command-open]").forEach((button) => {
      button.setAttribute("aria-haspopup", "dialog");
      button.setAttribute("aria-controls", "admin-command-palette");
    });

    const overlay = document.querySelector("[data-command-overlay]");
    if (overlay) {
      overlay.id = "admin-command-palette";
      overlay.setAttribute("role", "dialog");
      overlay.setAttribute("aria-modal", "true");
      overlay.setAttribute("aria-label", "Поиск и быстрые действия");
    }

    syncSidebarAria();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAccessibility, {once: true});
  } else {
    initAccessibility();
  }
})();
