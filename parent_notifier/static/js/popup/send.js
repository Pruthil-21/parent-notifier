// Sending one parent's message. The WhatsApp tab is opened blank inside the click (so
// pop-up blockers allow it and one named tab is reused), then the send is logged, and
// only when the server accepts it does the tab go to WhatsApp Web with the text the
// server rendered and stored.

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
    throw new Error(data.error ?? "The send could not be saved. Reload the page and try again.");
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
