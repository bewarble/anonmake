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

  function scrollInvalidBlock(field, behavior = 'smooth') {
    const block = containerFor(field) || field;
    const viewport = window.visualViewport;
    const viewportHeight = viewport?.height || window.innerHeight;
    const viewportOffsetTop = viewport?.offsetTop || 0;
    const rect = block.getBoundingClientRect();

    // Keep the complete field block in the upper-middle portion of the visible
    // viewport. iOS Safari is more reliable with explicit window.scrollTo than
    // with scrollIntoView after form validation/focus changes.
    const desiredTop = Math.max(88, Math.min(150, viewportHeight * 0.22));
    const target = Math.max(
      0,
      window.scrollY + rect.top - viewportOffsetTop - desiredTop
    );
    window.scrollTo({ top: target, behavior });
  }

  function focusFirstInvalid(form) {
    const invalid = [...form.querySelectorAll(fieldSelector)].find((field) => !field.validity.valid);
    if (!invalid) return;
    showError(invalid);

    // Move first, then focus without allowing Safari to override our scroll.
    scrollInvalidBlock(invalid, 'smooth');
    setTimeout(() => {
      invalid.focus({ preventScroll: true });
      scrollInvalidBlock(invalid, 'auto');
    }, 120);

    // Recalculate after iOS settles its visual viewport/browser chrome.
    setTimeout(() => scrollInvalidBlock(invalid, 'auto'), 320);
    setTimeout(() => scrollInvalidBlock(invalid, 'auto'), 650);
  }

  document.querySelectorAll('form').forEach((form) => {
    const fields = form.querySelectorAll(fieldSelector);
    if (!fields.length) return;

    fields.forEach((field) => {
      field.addEventListener('invalid', (event) => {
        event.preventDefault();
        showError(field);
      });
      field.addEventListener('input', () => {
        if (field.validity.valid) clearError(field);
        else if (field.getAttribute('aria-invalid') === 'true') showError(field);
      });
      field.addEventListener('change', () => {
        if (field.validity.valid) clearError(field);
      });
    });

    form.addEventListener('submit', (event) => {
      if (form.checkValidity()) return;
      event.preventDefault();
      fields.forEach((field) => {
        if (!field.validity.valid) showError(field);
      });
      requestAnimationFrame(() => focusFirstInvalid(form));
    }, true);
  });
})();
