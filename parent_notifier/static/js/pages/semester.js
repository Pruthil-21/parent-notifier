// Entry module for the class and semester pages.

import { initDialogs } from "../components/dialogs.js";
import { initPopup } from "../popup/controller.js";
import { initQueue } from "../popup/queue.js";
import { initSendingAs } from "../popup/sending-as.js";

initDialogs();
initSendingAs();
const popup = initPopup();
if (popup) initQueue(popup);

// The status filter applies as soon as it changes; without JavaScript, Apply does it.
for (const control of document.querySelectorAll("[data-auto-submit]")) {
  control.addEventListener("change", () => control.form?.requestSubmit());
}
