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
