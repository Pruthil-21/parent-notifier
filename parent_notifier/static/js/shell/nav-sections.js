// Sections with sub-items, such as Classes: each folds away (remembered per browser),
// and a long one can be narrowed by typing. The section holding the current page
// always opens, so the mentor can see where they are.

const STORAGE_KEY = "parent-notifier.nav-folded";

function readFolded() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "[]");
    return new Set(Array.isArray(saved) ? saved : []);
  } catch {
    return new Set(); // storage blocked or unreadable: every section starts open
  }
}

function saveFolded(folded) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...folded]));
  } catch {
    // Not remembering the fold is harmless.
  }
}

const folded = readFolded();

function setUpSection(section) {
  const id = section.dataset.navSection;
  const label = section.dataset.navLabel;
  const list = section.querySelector(".nav-pane__children");
  const fold = section.querySelector("[data-nav-fold]");
  const filterToggle = section.querySelector("[data-nav-filter-toggle]");
  const filterBox = section.querySelector(".nav-pane__filter");
  const input = filterBox?.querySelector("input");
  const empty = filterBox?.querySelector("[data-nav-filter-empty]");
  if (!list || !fold) return;

  function applyFilter() {
    const query = input.value.trim().toLowerCase();
    let shown = 0;
    for (const item of list.children) {
      const match = item.textContent.toLowerCase().includes(query);
      item.hidden = !match;
      if (match) shown += 1;
    }
    empty.hidden = shown > 0;
  }

  function closeFilter() {
    if (!filterBox || filterBox.hidden) return;
    input.value = "";
    applyFilter();
    filterBox.hidden = true;
    filterToggle.setAttribute("aria-expanded", "false");
  }

  function setOpen(open) {
    list.hidden = !open;
    fold.setAttribute("aria-expanded", String(open));
    fold.title = open ? `Hide the ${label.toLowerCase()} list` : `Show the ${label.toLowerCase()} list`;
    if (!open) closeFilter();
  }

  const holdsCurrent = list.querySelector("[aria-current]") !== null;
  setOpen(holdsCurrent || !folded.has(id));
  fold.hidden = false;
  fold.addEventListener("click", () => {
    const open = list.hidden;
    setOpen(open);
    if (open) folded.delete(id);
    else folded.add(id);
    saveFolded(folded);
  });

  if (!filterToggle || !filterBox) return;
  filterToggle.hidden = false;
  filterToggle.addEventListener("click", () => {
    if (!filterBox.hidden) {
      closeFilter();
      return;
    }
    setOpen(true);
    filterBox.hidden = false;
    filterToggle.setAttribute("aria-expanded", "true");
    input.focus();
  });
  input.addEventListener("input", applyFilter);
  input.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    // Closes the filter only, not the navigation drawer around it.
    event.stopPropagation();
    closeFilter();
    filterToggle.focus();
  });
}

document.querySelectorAll("[data-nav-section]").forEach(setUpSection);
