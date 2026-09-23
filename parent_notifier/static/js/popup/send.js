// Sending one parent's message. The WhatsApp tab is opened blank inside the click (so
// pop-up blockers allow it and one named tab is reused), then the send is logged, and
// only when the server accepts it does the tab go to WhatsApp Web with the text the
// server rendered and stored.

import { confirmThen } from "./sending-as.js";

const TAB_NAME = "parent-notifier-whatsapp";

function csrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content ?? "";
}

export async function postLog(url, body) {
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error("Could not reach Parent Notifier. Check the connection and try again.");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.error ?? "The send could not be saved. Reload the page and try again.");
    error.pacing = data.pacing; // a refused send still says how long to wait
    throw error;
  }
  return data;
}

function closeIfBlank(tab) {
  try {
    if (tab && tab.location.href === "about:blank") tab.close();
  } catch {
    // Already on WhatsApp Web from an earlier send: leave it open.
  }
}

// Must be called straight from a click handler, before any await.
export async function sendToParent(logUrl, language, note) {
  const tab = window.open("", TAB_NAME);
  try {
    if (tab) tab.opener = null; // WhatsApp's page must not be able to steer this one
  } catch {
    // Already cross-origin from an earlier send: it had no opener to clear.
  }
  let data;
  try {
    data = await postLog(logUrl, { status: "sent", language, note });
  } catch (error) {
    closeIfBlank(tab);
    throw error;
  }
  if (tab) {
    tab.location.href = data.whatsappUrl;
  } else {
    window.open(data.whatsappUrl, TAB_NAME); // pop-ups blocked: try once more
  }
  return data;
}

// The popup's Send button: disabled with the reason when there is no valid number.
export function initSendButton(popup) {
  const button = popup.dialog.querySelector("[data-popup-send]");
  const status = popup.dialog.querySelector('[data-slot="send-note"]');
  const say = (text, isError = false) => {
    status.textContent = text;
    status.classList.toggle("is-error", isError);
  };

  popup.onShow((student) => {
    // Pacing decides the final disabled state from this and its own countdown.
    button.dataset.noPhone = String(!student.phoneValid);
    say(student.phoneValid ? "" : "This parent has no valid mobile number. Edit the student to fix it.");
  });

  button.addEventListener("click", () => confirmThen(send));

  async function send() {
    const { id, link } = popup.current();
    button.setAttribute("aria-busy", "true");
    try {
      const data = await sendToParent(link.dataset.logUrl, popup.language(), popup.note());
      popup.markDone(id, data.label);
      popup.pacing.update(data.pacing);
      say("Opened in WhatsApp Web. Press send there to deliver it.");
    } catch (error) {
      if (error.pacing) popup.pacing.update(error.pacing);
      say(error.message, true);
    } finally {
      button.removeAttribute("aria-busy");
    }
  }
}
