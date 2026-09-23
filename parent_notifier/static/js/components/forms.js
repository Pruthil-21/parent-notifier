// Show and hide buttons on password fields. The buttons ship hidden, so without
// JavaScript the field is a plain password input.

function setVisible(input, button, visible) {
  input.type = visible ? "text" : "password";
  button.textContent = visible ? "Hide" : "Show";
  button.setAttribute("aria-label", visible ? "Hide password" : "Show password");
}

export function initPasswordToggles(root = document) {
  for (const button of root.querySelectorAll("[data-password-toggle]")) {
    const input = document.getElementById(button.getAttribute("aria-controls"));
    if (!input) continue;
    button.hidden = false;
    button.addEventListener("click", () => {
      setVisible(input, button, input.type === "password");
      input.focus();
    });
    // Submit as a password field so the browser never offers to save it as plain text.
    input.form?.addEventListener("submit", () => setVisible(input, button, false));
  }
}
