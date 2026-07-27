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
