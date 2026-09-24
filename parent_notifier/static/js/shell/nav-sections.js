// Menu sections and the groups inside them (departments, Past batches, a mentor's
// classes) fold away, each remembered per browser. A group holding the current page
// always opens, so you can see where you are. A section with a filter narrows every
// group inside it as you type.

const STORAGE_KEY = "parent-notifier.nav-open";

function readSaved() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}");
    return saved && typeof saved === "object" && !Array.isArray(saved) ? saved : {};
  } catch {
    return {}; // storage blocked or unreadable: every group starts as the page says
  }
}

function save(saved) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
  } catch {
    // Not remembering the fold is harmless.
  }
}

const saved = readSaved();
const groups = new Map();

function childList(element) {
  return element.querySelector(":scope > .nav-pane__children");
}

function setUpGroup(group) {
  const id = group.dataset.navGroup;
  const label = group.dataset.navLabel;
  const row = group.querySelector(":scope > .nav-pane__row");
  const fold = row?.querySelector("[data-nav-fold]");
  const list = childList(group);
  if (!fold || !list) return;

  const holdsCurrent = list.querySelector("[aria-current]") !== null;
  const byDefault = group.dataset.navDefault !== "closed";

  function setOpen(open) {
    list.hidden = !open;
    fold.setAttribute("aria-expanded", String(open));
    fold.title = open ? `Hide ${label}` : `Show ${label}`;
    if (!open) group.dispatchEvent(new CustomEvent("nav:folded"));
  }

  function toggle() {
    const open = list.hidden;
    setOpen(open);
    saved[id] = open;
    save(saved);
  }

  setOpen(holdsCurrent || (saved[id] ?? byDefault));
  fold.hidden = false;
  fold.addEventListener("click", toggle);
  row.querySelector("[data-nav-group-label]")?.addEventListener("click", toggle);
  groups.set(group, {
    setOpen,
    restore: () => setOpen(holdsCurrent || (saved[id] ?? byDefault)),
  });
}

function text(element) {
  return element.textContent.toLowerCase();
}

function showEverything(list) {
  for (const item of list.querySelectorAll("li")) item.hidden = false;
}

// Shows the entries of a list that match, and each group holding a match (opened for
// now); a matching group or year heading shows everything under it. Returns whether
// anything in the list is shown.
function narrow(list, query) {
  let anyShown = false;
  let heading = null;
  let headingMatches = false;
  let headingHasShown = false;
  const closeHeading = () => {
    if (heading) heading.hidden = !headingHasShown;
  };
  for (const item of list.children) {
    if (item.classList.contains("nav-pane__heading")) {
      closeHeading();
      heading = item;
      headingMatches = text(item).includes(query);
      headingHasShown = false;
      continue;
    }
    let shown;
    const inner = childList(item);
    if (item.hasAttribute("data-nav-group") && inner) {
      const row = item.querySelector(":scope > .nav-pane__row");
      if (headingMatches || text(row).includes(query)) {
        showEverything(inner);
        shown = true;
      } else {
        shown = narrow(inner, query);
      }
      if (shown) groups.get(item)?.setOpen(true);
    } else {
      shown = headingMatches || text(item).includes(query);
    }
    item.hidden = !shown;
    if (shown) {
      anyShown = true;
      headingHasShown = true;
    }
  }
  closeHeading();
  return anyShown;
}

function setUpFilter(section) {
  const filterToggle = section.querySelector(":scope > .nav-pane__row [data-nav-filter-toggle]");
  const filterBox = section.querySelector(":scope > .nav-pane__filter");
  const list = childList(section);
  if (!filterToggle || !filterBox || !list) return;
  const input = filterBox.querySelector("input");
  const empty = filterBox.querySelector("[data-nav-filter-empty]");

  function applyFilter() {
    const query = input.value.trim().toLowerCase();
    if (!query) {
      showEverything(list);
      for (const group of list.querySelectorAll("[data-nav-group]")) groups.get(group)?.restore();
      empty.hidden = true;
      return;
    }
    empty.hidden = narrow(list, query);
  }

  function closeFilter() {
    if (filterBox.hidden) return;
    input.value = "";
    applyFilter();
    filterBox.hidden = true;
    filterToggle.setAttribute("aria-expanded", "false");
  }

  filterToggle.hidden = false;
  filterToggle.addEventListener("click", () => {
    if (!filterBox.hidden) {
      closeFilter();
      return;
    }
    groups.get(section)?.setOpen(true);
    filterBox.hidden = false;
    filterToggle.setAttribute("aria-expanded", "true");
    input.focus();
  });
  section.addEventListener("nav:folded", (event) => {
    if (event.target === section) closeFilter();
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

// Inner groups first, so a section's current-page check sees them already set up.
[...document.querySelectorAll("[data-nav-group]")].reverse().forEach(setUpGroup);
document.querySelectorAll("[data-nav-section]").forEach(setUpFilter);
