// Entry module for the class and semester pages.

import { initDialogs } from "../components/dialogs.js";
import { initPopup } from "../popup/controller.js";

initDialogs();
initPopup();

// The status filter applies as soon as it changes; without JavaScript, Apply does it.
for (const control of document.querySelectorAll("[data-auto-submit]")) {
  control.addEventListener("change", () => control.form?.requestSubmit());
}
