/* Stage 51 — unified admin action and confirmation UX. */
"use strict";

(() => {
  let pending = null;

  const modal = document.createElement("div");
  modal.className = "admin-action-overlay";
  modal.hidden = true;
  modal.innerHTML = `
    <section class="admin-action-dialog" role="dialog" aria-modal="true" aria-labelledby="admin-action-title" aria-describedby="admin-action-message">
      <div class="admin-action-icon" aria-hidden="true">!</div>
      <div class="admin-action-copy">
        <span class="admin-action-eyebrow">Подтверждение действия</span>
        <h2 id="admin-action-title">Подтвердите действие</h2>
        <p id="admin-action-message">Это действие изменит данные.</p>
      </div>
      <div class="admin-action-buttons">
        <button type="button" class="button-secondary" data-action-cancel>Отмена</button>
        <button type="button" class="button-primary admin-action-confirm" data-action-confirm>Продолжить</button>
      </div>
    </section>`;
  document.body.appendChild(modal);

  const title = modal.querySelector("#admin-action-title");
  const message = modal.querySelector("#admin-action-message");
  const confirmButton = modal.querySelector("[data-action-confirm]");
  const cancelButton = modal.querySelector("[data-action-cancel]");

  function closeModal() {
    const restoreFocus = pending?.submitter;
    pending = null;
    modal.hidden = true;
    document.body.classList.remove("admin-action-modal-open");
    restoreFocus?.focus?.();
  }

  function openModal(form, submitter) {
    pending = {form, submitter};
    title.textContent = form.dataset.confirmTitle || "Подтвердите действие";
    message.textContent = form.dataset.confirm || "Это действие изменит данные. Продолжить?";
    confirmButton.textContent = form.dataset.confirmLabel || "Продолжить";
    confirmButton.classList.toggle("danger", form.dataset.confirmTone === "danger");
    modal.hidden = false;
    document.body.classList.add("admin-action-modal-open");
    requestAnimationFrame(() => cancelButton.focus());
  }

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if ((form.method || "get").toLowerCase() !== "post") return;

    const submitter = event.submitter || form.querySelector('button[type="submit"],input[type="submit"]');

    if (form.dataset.confirm && form.dataset.stage51Confirmed !== "1") {
      event.preventDefault();
      event.stopPropagation();
      openModal(form, submitter);
      return;
    }

    delete form.dataset.stage51Confirmed;
    form.classList.add("is-submitting");
    if (submitter && !submitter.dataset.loadingApplied) {
      submitter.dataset.loadingApplied = "1";
      submitter.dataset.originalLabel = submitter.textContent || "";
      const label = submitter.dataset.loadingLabel || form.dataset.loadingLabel || "Выполняем…";
      if (submitter.tagName === "BUTTON") submitter.textContent = label;
    }
  }, true);

  confirmButton.addEventListener("click", () => {
    if (!pending) return;
    const {form, submitter} = pending;
    pending = null;
    modal.hidden = true;
    document.body.classList.remove("admin-action-modal-open");
    form.dataset.stage51Confirmed = "1";
    if (submitter instanceof HTMLElement && typeof form.requestSubmit === "function") {
      form.requestSubmit(submitter);
    } else {
      form.requestSubmit();
    }
  });

  cancelButton.addEventListener("click", closeModal);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModal();
  });
  document.addEventListener("keydown", (event) => {
    if (!modal.hidden && event.key === "Escape") {
      event.preventDefault();
      closeModal();
    }
  });

  window.addEventListener("pageshow", () => {
    document.querySelectorAll("form.is-submitting").forEach((form) => form.classList.remove("is-submitting"));
    document.querySelectorAll("[data-loading-applied]").forEach((button) => {
      if (button.dataset.originalLabel !== undefined && button.tagName === "BUTTON") {
        button.textContent = button.dataset.originalLabel;
      }
      delete button.dataset.loadingApplied;
      delete button.dataset.originalLabel;
    });
  });
})();
