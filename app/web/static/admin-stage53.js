(() => {
  const bar = document.createElement('div');
  bar.className = 'admin-page-loading';
  bar.setAttribute('aria-hidden', 'true');
  document.body.appendChild(bar);

  function startLoading(scope) {
    bar.classList.add('is-active');
    (scope || document.body).classList.add('is-data-loading');
  }

  function stopLoading() {
    bar.classList.remove('is-active');
    document.querySelectorAll('.is-data-loading').forEach((node) => node.classList.remove('is-data-loading'));
  }

  document.querySelectorAll('form[data-data-filter]').forEach((form) => {
    form.addEventListener('submit', () => startLoading(form.closest('[data-data-scope]') || form));
  });

  document.querySelectorAll('a[data-data-nav]').forEach((link) => {
    link.addEventListener('click', () => startLoading(link.closest('[data-data-scope]') || document.body));
  });

  document.querySelectorAll('[data-stale-after]').forEach((node) => {
    const raw = node.dataset.staleAfter;
    const updated = node.dataset.updatedAt;
    if (!raw || !updated) return;
    const maxAgeSeconds = Number(raw);
    const updatedAt = Date.parse(updated);
    if (!Number.isFinite(maxAgeSeconds) || Number.isNaN(updatedAt)) return;
    if ((Date.now() - updatedAt) / 1000 <= maxAgeSeconds) return;
    node.classList.add('is-stale');
    if (!node.querySelector('.admin-stale-badge')) {
      const badge = document.createElement('span');
      badge.className = 'admin-stale-badge';
      badge.textContent = node.dataset.staleLabel || 'Данные устарели';
      node.prepend(badge);
    }
  });

  window.addEventListener('pageshow', stopLoading);
})();
