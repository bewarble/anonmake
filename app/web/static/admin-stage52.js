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

  function centerInvalidBlock(field, behavior = 'smooth') {
    const block = containerFor(field) || field;
    block.scrollIntoView({ behavior, block: 'center', inline: 'nearest' });
  }

  function focusFirstInvalid(form) {
    const invalid = [...form.querySelectorAll(fieldSelector)].find((field) => !field.validity.valid);
    if (!invalid) return;
    showError(invalid);

    // First position the complete field block, including the inline error.
    centerInvalidBlock(invalid);
    invalid.focus({ preventScroll: true });

    // Mobile browsers resize the visual viewport after focus/keyboard opening.
    // Re-center after that resize so the error text remains visible as well.
    setTimeout(() => centerInvalidBlock(invalid), 180);
    setTimeout(() => centerInvalidBlock(invalid, 'auto'), 420);
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
