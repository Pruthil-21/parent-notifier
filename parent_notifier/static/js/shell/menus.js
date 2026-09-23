// Small menus built on <details>: the browser opens and closes them; this adds closing
// on Escape (focus returns to the button), on a click outside, and when another opens.

const menus = [...document.querySelectorAll("details[data-menu]")];

function close(menu, { returnFocus = false } = {}) {
  if (!menu.open) return;
  menu.open = false;
  if (returnFocus) menu.querySelector("summary")?.focus();
}

for (const menu of menus) {
  menu.addEventListener("toggle", () => {
    if (!menu.open) return;
    for (const other of menus) if (other !== menu) close(other);
  });
  menu.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close(menu, { returnFocus: true });
  });
}

document.addEventListener("click", (event) => {
  for (const menu of menus) if (!menu.contains(event.target)) close(menu);
});
