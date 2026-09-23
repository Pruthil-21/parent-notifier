// Pacing in the popup: Send waits out the gap between messages with a countdown, a longer
// pause follows each burst, and the day stops at the daily limit, which the server also
// enforces. The server sends seconds to wait, so the computer's own clock does not matter.

function clockText(seconds) {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}

function describe(state, left) {
  const count = `${state.sentToday} of ${state.dailyLimit} sent today`;
  if (state.reason === "daily") {
    return `Today's limit of ${state.dailyLimit} messages is reached. Sending opens again tomorrow.`;
  }
  if (left > 0 && state.reason === "burst") {
    return `Short pause to protect your WhatsApp number: ${clockText(left)} left · ${count}`;
  }
  if (left > 0) return `Next send in ${left} s · ${count}`;
  return count;
}

export function initPacing(popup) {
  const { dialog } = popup;
  const note = dialog.querySelector('[data-slot="pacing"]');
  const buttons = [...dialog.querySelectorAll("[data-popup-send], [data-queue-send]")];
  let state = {};
  let timer = null;

  function secondsLeft() {
    return Math.max(0, Math.ceil((state.deadline - Date.now()) / 1000));
  }

  function refresh() {
    const left = secondsLeft();
    const waiting = state.reason === "daily" || left > 0;
    for (const button of buttons) {
      button.disabled = waiting || button.dataset.noPhone === "true";
    }
    note.textContent = describe(state, left);
    if (!waiting && timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  function update(pacing) {
    state = { ...pacing, deadline: Date.now() + pacing.waitSeconds * 1000 };
    if (!timer && pacing.waitSeconds > 0) timer = setInterval(refresh, 1000);
    refresh();
  }

  update({
    waitSeconds: Number(dialog.dataset.waitSeconds),
    reason: dialog.dataset.waitReason || null,
    sentToday: Number(dialog.dataset.sentToday),
    dailyLimit: Number(dialog.dataset.dailyLimit),
  });
  popup.onShow(refresh);
  return { update, current: () => ({ ...state, waitSeconds: secondsLeft() }) };
}
