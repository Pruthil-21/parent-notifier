// Dismiss buttons on message bars. Focus moves to the main area so keyboard users are not
// left on a removed element.

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-dismiss-message]");
  if (!button) return;
  const bar = button.closest("[data-message-bar]");
  if (!bar) return;
  bar.remove();
  document.getElementById("main")?.focus();
});
