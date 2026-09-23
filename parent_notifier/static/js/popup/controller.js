// Opening the student popup from the grid and moving through the students shown.
// Previous and Next follow the grid as it is filtered and sorted. Without JavaScript the
// names are plain links to each student's page.

import { renderStudent } from "./render.js";

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

  function show(id) {
    const student = students.get(id);
    if (!student) return;
    currentId = id;
    renderStudent(dialog, student, rules);
    const ids = links().map((link) => link.dataset.studentLink);
    const index = ids.indexOf(id);
    position.textContent = `${index + 1} of ${ids.length}`;
    dialog.querySelector("[data-popup-edit]").href = links()[index]?.dataset.editUrl ?? "#";
    dialog.querySelector('[data-popup-move="-1"]').disabled = index <= 0;
    dialog.querySelector('[data-popup-move="1"]').disabled = index >= ids.length - 1;
    if (!dialog.open) dialog.showModal();
  }

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
