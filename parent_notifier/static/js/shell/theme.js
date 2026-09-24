// The theme menu: switch the page at once, then save the choice on the account in the
// background. If saving fails, the form is sent the ordinary way, so nothing is lost.

const menu = document.querySelector("[data-theme-menu]");

function show(button) {
  document.documentElement.dataset.theme = button.value;
  for (const option of menu.querySelectorAll("button[name=theme]")) {
    option.setAttribute("aria-pressed", String(option === button));
  }
  const summary = menu.querySelector("summary");
  summary.replaceChildren(button.querySelector("svg").cloneNode(true));
  summary.setAttribute("aria-label", `Theme: ${button.dataset.label}`);
}

if (menu) {
  const form = menu.querySelector("form");
  form.addEventListener("submit", async (event) => {
    const button = event.submitter;
    if (!button?.value) return;
    event.preventDefault();
    show(button);
    menu.open = false;
    menu.querySelector("summary").focus();
    const body = new FormData(form);
    body.set("theme", button.value);
    try {
      const response = await fetch(form.action, {
        method: "POST",
        body,
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`Theme not saved: ${response.status}`);
    } catch {
      const field = Object.assign(document.createElement("input"), {
        type: "hidden",
        name: "theme",
        value: button.value,
      });
      form.append(field);
      form.submit();
    }
  });
}
