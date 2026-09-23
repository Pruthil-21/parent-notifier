// Copying text to the clipboard. The Clipboard API only exists on HTTPS or localhost, and
// the college server may serve plain HTTP, so there is a fallback through a hidden
// textarea and execCommand.

function copyWithTextarea(text) {
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  // CSSOM styles are allowed by the content security policy; style attributes are not.
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.append(area);
  area.select();
  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    area.remove();
  }
}

export async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Permission refused: try the older way below.
    }
  }
  return copyWithTextarea(text);
}

// Buttons with data-copy-target="<id>" copy that element's text and report the result
// in the live region marked data-copy-status="<id>".
export function initCopyButtons(root = document) {
  for (const button of root.querySelectorAll("[data-copy-target]")) {
    const source = document.getElementById(button.dataset.copyTarget);
    const status = document.querySelector(`[data-copy-status="${button.dataset.copyTarget}"]`);
    if (!source) continue;
    button.hidden = false;
    button.addEventListener("click", async () => {
      const copied = await copyText(source.textContent.trim());
      if (status) {
        status.textContent = copied
          ? "Copied. Paste it somewhere safe, such as a notes app or your email drafts."
          : "Could not copy. Select the code and copy it yourself.";
      }
    });
  }
}
