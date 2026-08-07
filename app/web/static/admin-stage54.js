(() => {
  const focusableSelector = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

  document.querySelectorAll('.pro-nav a.active').forEach((link) => link.setAttribute('aria-current', 'page'));
  document.querySelectorAll('.table-wrap').forEach((wrap) => {
    wrap.setAttribute('tabindex', '0');
    if (!wrap.getAttribute('aria-label')) wrap.setAttribute('aria-label', 'Прокручиваемая таблица');
  });

  const sidebar = document.querySelector('[data-sidebar]');
  document.querySelectorAll('[data-sidebar-toggle]').forEach((button) => {
    button.setAttribute('aria-controls', 'admin-sidebar');
    button.setAttribute('aria-expanded', 'false');
  });
  if (sidebar) sidebar.id = 'admin-sidebar';

  const commandOverlay = document.querySelector('[data-command-overlay]');
  if (commandOverlay) {
    commandOverlay.setAttribute('role', 'dialog');
    commandOverlay.setAttribute('aria-modal', 'true');
    commandOverlay.setAttribute('aria-label', 'Поиск и быстрые действия');
  }
  const commandInput = document.querySelector('[data-command-input]');
  if (commandInput) commandInput.setAttribute('aria-label', 'Поиск раздела или действия');

  document.addEventListener('keydown', (event) => {
    const overlay = document.querySelector('.admin-action-overlay:not([hidden])');
    if (!overlay || event.key !== 'Tab') return;
    const items = [...overlay.querySelectorAll(focusableSelector)].filter((node) => node.offsetParent !== null);
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }, true);

  document.addEventListener('click', (event) => {
    const toggle = event.target.closest('[data-sidebar-toggle]');
    if (!toggle || !sidebar) return;
    requestAnimationFrame(() => {
      const open = sidebar.classList.contains('open') || document.body.classList.contains('sidebar-open');
      document.querySelectorAll('[data-sidebar-toggle]').forEach((button) => button.setAttribute('aria-expanded', open ? 'true' : 'false'));
    });
  });
})();
