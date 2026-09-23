// Entry module for the recovery code page: copy button, and Continue stays disabled until
// the mentor ticks "I have saved this code". The server checks the box as well.

import { initCopyButtons } from "../components/clipboard.js";

initCopyButtons();

const saved = document.querySelector('input[name="saved"]');
const continueButton = document.querySelector("[data-continue]");

if (saved && continueButton) {
  const sync = () => {
    continueButton.disabled = !saved.checked;
  };
  saved.addEventListener("change", sync);
  sync();
}
