// Opening the student popup from the grid and moving through the students shown.
// Previous and Next follow the grid as it is filtered and sorted. Without JavaScript the
// names are plain links to each student's page.

import { renderMessage, renderStudent } from "./render.js";
import { sendToParent } from "./send.js";

const LANGUAGE_KEY = "parent-notifier.language";

function savedLanguage(fallback) {
  try {
    return window.sessionStorage.getItem(LANGUAGE_KEY) || fallback;
  } catch {
    return fallback; // storage blocked: use the profile default
  }
}

export function initPopup() {
  const dialog = document.getElementById("student-popup");
  const dataBlock = document.getElementById("students-data");
  if (!(dialog instanceof HTMLDialogElement) || !dataBlock) return;

  const students = new Map(JSON.parse(dataBlock.textContent).map((s) => [String(s.id), s]));
  const rules = {
    threshold: Number(dialog.dataset.threshold),
    passMark: Number(dialog.dataset.passMark),
    midsemMax: Number(dialog.dataset.midsemMax),
  };
  const links = () => [...document.querySelectorAll("[data-student-link]")];
  const position = dialog.querySelector('[data-slot="position"]');
  let currentId = null;
  // The mentor's choice lasts for this browser session; it starts from the profile.
  let language = savedLanguage(dialog.dataset.defaultLanguage);
  const languageInputs = [...dialog.querySelectorAll('[name="popup-language"]')];
  const syncLanguage = () => {
    for (const input of languageInputs) input.checked = input.value === language;
  };
  syncLanguage();
  for (const input of languageInputs) {
    input.addEventListener("change", () => {
      language = input.value;
      try {
        window.sessionStorage.setItem(LANGUAGE_KEY, language);
      } catch {
        // Not remembering the choice is harmless.
      }
      renderMessage(dialog, students.get(currentId), language);
    });
  }

  function show(id) {
    const student = students.get(id);
    if (!student) return;
    currentId = id;
    renderStudent(dialog, student, rules);
    renderMessage(dialog, student, language);
    const ids = links().map((link) => link.dataset.studentLink);
    const index = ids.indexOf(id);
    position.textContent = `${index + 1} of ${ids.length}`;
    dialog.querySelector("[data-popup-edit]").href = links()[index]?.dataset.editUrl ?? "#";
    showSendState(student);
    dialog.querySelector('[data-popup-move="-1"]').disabled = index <= 0;
    dialog.querySelector('[data-popup-move="1"]').disabled = index >= ids.length - 1;
    if (!dialog.open) dialog.showModal();
  }

  const sendButton = dialog.querySelector("[data-popup-send]");
  const sendNote = dialog.querySelector('[data-slot="send-note"]');

  function showSendState(student) {
    sendButton.disabled = !student.phoneValid;
    sendNote.textContent = student.phoneValid
      ? ""
      : "This parent has no valid mobile number. Edit the student to fix it, then send.";
    sendNote.classList.remove("is-error");
  }

  function markSent(id, label) {
    const student = students.get(id);
    student.mark = label;
    dialog.querySelector('[data-slot="mark"]').textContent = label;
    const cell = document.querySelector(`[data-message-cell="${id}"]`);
    if (cell) {
      cell.textContent = label;
      cell.className = "message-done";
    }
  }

  sendButton.addEventListener("click", async () => {
    const id = currentId;
    const link = links().find((item) => item.dataset.studentLink === id);
    sendButton.setAttribute("aria-busy", "true");
    try {
      const data = await sendToParent(link.dataset.logUrl, language, "");
      markSent(id, data.label);
      sendNote.textContent = "Opened in WhatsApp Web. Press send there to deliver it.";
    } catch (error) {
      sendNote.textContent = error.message;
      sendNote.classList.add("is-error");
    } finally {
      sendButton.removeAttribute("aria-busy");
    }
  });

  function move(step) {
    const ids = links().map((link) => link.dataset.studentLink);
    const next = ids[ids.indexOf(currentId) + step];
    if (next) show(next);
  }

  document.addEventListener("click", (event) => {
    const link = event.target.closest("[data-student-link]");
    // Keep new-tab and new-window clicks working as ordinary links.
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey) return;
    event.preventDefault();
    show(link.dataset.studentLink);
  });

  for (const button of dialog.querySelectorAll("[data-popup-move]")) {
    button.addEventListener("click", () => move(Number(button.dataset.popupMove)));
  }

  dialog.addEventListener("keydown", (event) => {
    if (event.target.closest("input, textarea, select")) return;
    if (event.key === "ArrowLeft") move(-1);
    if (event.key === "ArrowRight") move(1);
  });

  // Focus returns to the student the mentor ended on, not the one they first opened.
  dialog.addEventListener("close", () => {
    links()
      .find((link) => link.dataset.studentLink === currentId)
      ?.focus();
  });
}
