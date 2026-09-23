// The once-per-session question "Is WhatsApp Web signed in to +91 ...?". A send waits
// until the mentor answers Yes; that same click then runs it, so the browser still
// treats the WhatsApp tab as opened by the mentor and does not block it.

const CONFIRMED_KEY = "parent-notifier.sending-as-confirmed";

function confirmed() {
  try {
    return window.sessionStorage.getItem(CONFIRMED_KEY) === "yes";
  } catch {
    return false; // storage blocked: ask each time rather than never
  }
}

function remember() {
  try {
    window.sessionStorage.setItem(CONFIRMED_KEY, "yes");
  } catch {
    // Asking again next time is harmless.
  }
}

let pending = null;

// Run `action` now if the number was confirmed this session, otherwise after Yes.
export function confirmThen(action) {
  const dialog = document.getElementById("sending-as");
  if (confirmed() || !(dialog instanceof HTMLDialogElement)) {
    action();
    return;
  }
  pending = action;
  dialog.showModal();
}

export function initSendingAs() {
  const dialog = document.getElementById("sending-as");
  dialog?.querySelector("[data-sending-as-confirm]")?.addEventListener("click", () => {
    remember();
    dialog.close();
    const action = pending;
    pending = null;
    action?.();
  });
  dialog?.addEventListener("close", () => {
    pending = null;
  });
}
