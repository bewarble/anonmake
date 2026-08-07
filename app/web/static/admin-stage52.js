(() => {
  const fieldSelector = 'input:not([type="hidden"]):not([type="submit"]), select, textarea';

  function messageFor(field) {
    const validity = field.validity;
    if (validity.valueMissing) return 'Заполните это поле.';
    if (validity.typeMismatch && field.type === 'email') return 'Введите корректный адрес электронной почты.';
    if (validity.tooShort) return `Введите не менее ${field.minLength} символов.`;
    if (validity.tooLong) return `Введите не более ${field.maxLength} символов.`;
    if (validity.rangeUnderflow) return `Значение должно быть не меньше ${field.min}.`;
    if (validity.rangeOverflow) return `Значение должно быть не больше ${field.max}.`;
    if (validity.patternMismatch) return field.dataset.validationMessage || 'Проверьте формат значения.';
    return field.dataset.validationMessage || 'Проверьте значение поля.';
  }

  function containerFor(field) {
    return field.closest('.form-field, .field, label') || field.parentElement;
  }

  function clearError(field) {
    field.removeAttribute('aria-invalid');
    const container = containerFor(field);
    container?.classList.remove('has-error');
    container?.querySelector(':scope > .admin-field-error')?.remove();
  }

  function showError(field) {
    if (field.validity.valid) {
      clearError(field);
      return;
    }
    const container = containerFor(field);
    if (!container) return;
    field.setAttribute('aria-invalid', 'true');
    container.classList.add('has-error');
    let error = container.querySelector(':scope > .admin-field-error');
    if (!error) {
      error = document.createElement('small');
      error.className = 'admin-field-error';
      error.setAttribute('role', 'alert');
      container.appendChild(error);
    }
    error.textContent = messageFor(field);
  }

  function isMobileViewport() {
    return window.matchMedia('(max-width: 760px), (pointer: coarse)').matches;
  }

  function scrollInvalidBlock(field, behavior = 'smooth') {
    const block = containerFor(field) || field;
    const rect = block.getBoundingClientRect();
    const viewport = window.visualViewport;
    const offsetTop = viewport?.offsetTop || 0;
    const pageTop = window.pageYOffset || document.documentElement.scrollTop || 0;
    const desiredTop = isMobileViewport() ? 112 : 150;
    const target = Math.max(0, pageTop + rect.top - offsetTop - desiredTop);
    window.scrollTo({ top: target, left: 0, behavior });
  }

  function revealFirstInvalid(form) {
    const invalid = [...form.querySelectorAll(fieldSelector)].find((field) => !field.validity.valid);
    if (!invalid) return;
    showError(invalid);

    scrollInvalidBlock(invalid, 'smooth');
    setTimeout(() => scrollInvalidBlock(invalid, 'auto'), 180);

    if (!isMobileViewport()) {
      setTimeout(() => invalid.focus({ preventScroll: true }), 120);
    }
  }

  document.querySelectorAll('form').forEach((form) => {
    const fields = form.querySelectorAll(fieldSelector);
    if (!fields.length) return;
    let invalidTimer = null;

    fields.forEach((field) => {
      field.addEventListener('invalid', (event) => {
        event.preventDefault();
        showError(field);

        // Constraint validation fires `invalid` for each bad field and aborts
        // submission before a `submit` event exists. Debounce the burst, then
        // reveal the first invalid control after all inline errors are rendered.
        clearTimeout(invalidTimer);
        invalidTimer = setTimeout(() => revealFirstInvalid(form), 0);
      });
      field.addEventListener('input', () => {
        if (field.validity.valid) clearError(field);
        else if (field.getAttribute('aria-invalid') === 'true') showError(field);
      });
      field.addEventListener('change', () => {
        if (field.validity.valid) clearError(field);
      });
    });
  });
})();
