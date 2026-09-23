// Navigation pane: collapses to an icon rail on wide screens (remembered per browser)
// and opens as a drawer over the content on narrow ones.

const STORAGE_KEY = "parent-notifier.nav-collapsed";
const narrowScreen = window.matchMedia("(max-width: 899px)");

const frame = document.querySelector("[data-app-frame]");
const pane = document.getElementById("nav-pane");
const toggle = document.querySelector("[data-nav-toggle]");
const collapseButton = document.querySelector("[data-nav-collapse]");
const collapseLabel = document.querySelector("[data-nav-collapse-label]");
const backdrop = document.querySelector("[data-nav-backdrop]");

function readCollapsed() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false; // storage blocked: fall back to the expanded pane
  }
}

function saveCollapsed(collapsed) {
  try {
    window.localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
  } catch {
    // Not saving the preference is harmless.
  }
}

function setCollapsed(collapsed) {
  frame.toggleAttribute("data-nav-collapsed", collapsed);
  const label = collapsed ? "Expand menu" : "Collapse menu";
  collapseButton.setAttribute("aria-expanded", String(!collapsed));
  collapseButton.title = label;
  collapseLabel.textContent = label;
  if (!narrowScreen.matches) {
    toggle.setAttribute("aria-expanded", String(!collapsed));
    toggle.setAttribute("aria-label", collapsed ? "Show navigation" : "Hide navigation");
  }
}

function setDrawer(open) {
  frame.toggleAttribute("data-nav-open", open);
  backdrop.hidden = !open;
  toggle.setAttribute("aria-expanded", String(open));
  toggle.setAttribute("aria-label", open ? "Hide navigation" : "Show navigation");
  if (open) {
    pane.querySelector("a, button")?.focus();
  }
}

function closeDrawer({ returnFocus }) {
  if (!frame.hasAttribute("data-nav-open")) return;
  setDrawer(false);
  if (returnFocus) toggle.focus();
}

function syncToScreen() {
  closeDrawer({ returnFocus: false });
  if (narrowScreen.matches) {
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "Show navigation");
  } else {
    setCollapsed(frame.hasAttribute("data-nav-collapsed"));
  }
}

if (frame && pane && toggle && collapseButton) {
  setCollapsed(readCollapsed());
  syncToScreen();

  toggle.addEventListener("click", () => {
    if (narrowScreen.matches) {
      setDrawer(!frame.hasAttribute("data-nav-open"));
    } else {
      const collapsed = !frame.hasAttribute("data-nav-collapsed");
      setCollapsed(collapsed);
      saveCollapsed(collapsed);
    }
  });

  collapseButton.addEventListener("click", () => {
    const collapsed = !frame.hasAttribute("data-nav-collapsed");
    setCollapsed(collapsed);
    saveCollapsed(collapsed);
  });

  backdrop.addEventListener("click", () => closeDrawer({ returnFocus: true }));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeDrawer({ returnFocus: true });
  });
  narrowScreen.addEventListener("change", syncToScreen);
}
