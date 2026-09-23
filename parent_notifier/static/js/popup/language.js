// The message language picker. The choice lasts for the browser session and starts from
// the mentor's profile setting (data-default-language on the popup).

const LANGUAGE_KEY = "parent-notifier.language";

function read(fallback) {
  try {
    return window.sessionStorage.getItem(LANGUAGE_KEY) || fallback;
  } catch {
    return fallback; // storage blocked: use the profile default
  }
}

function save(language) {
  try {
    window.sessionStorage.setItem(LANGUAGE_KEY, language);
  } catch {
    // Not remembering the choice is harmless.
  }
}

// Returns a getter for the current language; onChange runs after each switch.
export function initLanguage(dialog, onChange) {
  let language = read(dialog.dataset.defaultLanguage);
  for (const input of dialog.querySelectorAll('[name="popup-language"]')) {
    input.checked = input.value === language;
    input.addEventListener("change", () => {
      language = input.value;
      save(language);
      onChange();
    });
  }
  return () => language;
}
