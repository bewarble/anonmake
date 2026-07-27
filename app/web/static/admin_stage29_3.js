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
