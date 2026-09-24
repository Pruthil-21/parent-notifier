// Opening and closing small <dialog> elements. An opener is a link to a page with the
// same form, so without JavaScript it simply navigates there.

function openDialog(dialog) {
  dialog.showModal();
  const first = dialog.querySelector("input:not([type=hidden]), select, textarea");
  first?.focus();
  first?.select?.();
}

export function initDialogs(root = document) {
  for (const opener of root.querySelectorAll("[data-dialog-open]")) {
    const dialog = document.getElementById(opener.dataset.dialogOpen);
    if (!(dialog instanceof HTMLDialogElement)) continue;
    opener.addEventListener("click", (event) => {
      event.preventDefault();
      // An opener inside a menu leaves the menu open behind the dialog otherwise, and
      // focus comes back to the menu's button, since the item itself is hidden again.
      const menu = opener.closest("details[open]");
      if (menu) {
        menu.open = false;
        dialog.addEventListener("close", () => menu.querySelector("summary").focus(), { once: true });
      }
      openDialog(dialog);
    });
  }
  root.addEventListener("click", (event) => {
    const closer = event.target.closest("[data-dialog-close]");
    closer?.closest("dialog")?.close();
  });
}
