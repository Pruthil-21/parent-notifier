// Opening the student popup from the grid and moving through the students shown.
// Previous and Next follow the grid as it is filtered and sorted. Without JavaScript the
// names are plain links to each student's page. The popup object returned here is what
// the language, send and queue modules hook into.

import { initLanguage } from "./language.js";
import { initPacing } from "./pacing.js";
import { renderMessage, renderStudent } from "./render.js";
import { initSendButton } from "./send.js";

function createPopup(dialog, students) {
  const rules = {
    threshold: Number(dialog.dataset.threshold),
    midsemMax: Number(dialog.dataset.midsemMax),
  };
  const note = dialog.querySelector("[data-note]");
  const noteCount = dialog.querySelector('[data-slot="note-count"]');
  const showListeners = [];
  const links = () => [...document.querySelectorAll("[data-student-link]")];
  let currentId = null;

  const popup = {
    dialog,
    links,
    current: () => ({
      id: currentId,
      student: students.get(currentId),
      link: links().find((link) => link.dataset.studentLink === currentId),
    }),
    student: (id) => students.get(id),
    note: () => note.value,
    onShow: (listener) => showListeners.push(listener),
    refreshMessage: () => {
      noteCount.textContent = `${note.value.length} of ${note.maxLength}`;
      renderMessage(dialog, students.get(currentId), popup.language(), note.value);
    },
    show(id) {
      const student = students.get(id);
      if (!student) return;
      currentId = id;
      note.value = ""; // notes are written for one parent at a time
      renderStudent(dialog, student, rules);
      popup.refreshMessage();
      for (const listener of showListeners) listener(student);
      if (!dialog.open) dialog.showModal();
    },
    move(step) {
      const ids = links().map((link) => link.dataset.studentLink);
      const next = ids[ids.indexOf(currentId) + step];
      if (next) popup.show(next);
    },
    markDone(id, label) {
      students.get(id).mark = label;
      dialog.querySelector('[data-slot="mark"]').textContent = label;
      const cell = document.querySelector(`[data-message-cell="${id}"]`);
      if (cell) {
        cell.textContent = label;
        cell.className = "message-done";
      }
    },
  };
  popup.language = initLanguage(dialog, popup.refreshMessage);
  note.addEventListener("input", popup.refreshMessage);
  return popup;
}

function initBrowsing(popup) {
  const { dialog, links } = popup;
  popup.onShow(() => {
    const ids = links().map((link) => link.dataset.studentLink);
    const index = ids.indexOf(popup.current().id);
    dialog.querySelector('[data-slot="position"]').textContent = `${index + 1} of ${ids.length}`;
    dialog.querySelector("[data-popup-edit]").href = popup.current().link?.dataset.editUrl ?? "#";
    dialog.querySelector('[data-popup-move="-1"]').disabled = index <= 0;
    dialog.querySelector('[data-popup-move="1"]').disabled = index >= ids.length - 1;
  });
  document.addEventListener("click", (event) => {
    const link = event.target.closest("[data-student-link]");
    // Keep new-tab and new-window clicks working as ordinary links.
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey) return;
    event.preventDefault();
    popup.show(link.dataset.studentLink);
  });
  for (const button of dialog.querySelectorAll("[data-popup-move]")) {
    button.addEventListener("click", () => popup.move(Number(button.dataset.popupMove)));
  }
  dialog.addEventListener("keydown", (event) => {
    if (event.target.closest("input, textarea, select")) return;
    if (event.key === "ArrowLeft") popup.move(-1);
    if (event.key === "ArrowRight") popup.move(1);
  });
  // Focus returns to the student the mentor ended on, not the one they first opened.
  dialog.addEventListener("close", () => popup.current().link?.focus());
}

export function initPopup() {
  const dialog = document.getElementById("student-popup");
  const dataBlock = document.getElementById("students-data");
  if (!(dialog instanceof HTMLDialogElement) || !dataBlock) return null;
  const students = new Map(JSON.parse(dataBlock.textContent).map((s) => [String(s.id), s]));
  const popup = createPopup(dialog, students);
  initBrowsing(popup);
  initSendButton(popup);
  popup.pacing = initPacing(popup); // after the send button, so its checks run last
  return popup;
}
