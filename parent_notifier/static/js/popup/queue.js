// Queue mode: "Message pending parents" walks through every parent still to be messaged,
// in the grid's order, with Skip and Send and next. Without JavaScript the button is a
// link to the grid filtered to pending parents.

import { openLinkNote, postLog, sendToParent } from "./send.js";
import { confirmThen } from "./sending-as.js";

export function initQueue(popup) {
  const opener = document.querySelector("[data-queue-open]");
  if (!opener) return;
  const { dialog } = popup;
  const progress = dialog.querySelector("[data-queue-progress]");
  const done = dialog.querySelector("[data-queue-done]");
  const position = dialog.querySelector('[data-slot="queue-position"]');
  const bar = dialog.querySelector('[data-slot="queue-bar"]');
  const status = dialog.querySelector('[data-slot="send-note"]');
  const buttons = [...dialog.querySelectorAll("[data-queue-skip], [data-queue-send]")];
  let queue = [];
  let index = 0;

  function showCurrent() {
    if (index >= queue.length) {
      dialog.dataset.mode = "queue-done";
      done.hidden = false;
      bar.value = 1;
      return;
    }
    popup.show(queue[index]);
    position.textContent = `Parent ${index + 1} of ${queue.length}`;
    bar.value = index / queue.length;
  }

  opener.addEventListener("click", (event) => {
    event.preventDefault();
    queue = popup
      .links()
      .map((link) => link.dataset.studentLink)
      .filter((id) => popup.student(id)?.pending);
    index = 0;
    dialog.dataset.mode = "queue";
    progress.hidden = false;
    done.hidden = true;
    showCurrent();
  });

  async function advance(action) {
    const { id, link, student } = popup.current();
    for (const button of buttons) button.disabled = true;
    try {
      const data =
        action === "send"
          ? await sendToParent(link.dataset.logUrl, popup.language(), popup.note())
          : await postLog(link.dataset.logUrl, { status: "skipped", language: popup.language(), note: "" });
      popup.markDone(id, data.label);
      popup.pacing.update(data.pacing);
      student.pending = false;
      const next = () => {
        index += 1;
        showCurrent();
      };
      if (data.openUrl) {
        // A phone, or a blocked tab: the next parent comes up once Open WhatsApp is used.
        popup.showAppLink(data.openUrl, next);
        status.textContent = openLinkNote(data);
        status.classList.remove("is-error");
      } else {
        next();
      }
    } catch (error) {
      if (error.pacing) popup.pacing.update(error.pacing);
      status.textContent = error.message;
      status.classList.add("is-error");
    } finally {
      dialog.querySelector("[data-queue-skip]").disabled = false;
      popup.pacing.update(popup.pacing.current()); // Send and next follows the countdown
    }
  }

  dialog.querySelector("[data-queue-send]").addEventListener("click", () => {
    confirmThen(() => advance("send"));
  });
  dialog.querySelector("[data-queue-skip]").addEventListener("click", () => advance("skip"));

  dialog.addEventListener("close", () => {
    delete dialog.dataset.mode;
    progress.hidden = true;
    done.hidden = true;
  });
}
