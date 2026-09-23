// Fill the student popup from one student's data. Every value goes in with textContent,
// so a name or subject typed as HTML in a sheet stays plain text.

const BADGE_LABELS = {
  at_risk: "At risk",
  needs_attention: "Needs attention",
  doing_well: "Doing well",
  no_data: "No data",
  left: "Left",
  detained: "Detained",
};

function slot(dialog, name) {
  return dialog.querySelector(`[data-slot="${name}"]`);
}

function number(value) {
  return Number.isInteger(value) ? String(value) : String(Math.round(value * 10) / 10);
}

function figureCell(value, suffix, flagged, flagClass, flagText) {
  const cell = document.createElement("td");
  cell.className = "numeric";
  const figure = document.createElement("span");
  if (value === null) {
    figure.className = "text-muted";
    figure.textContent = "–";
    cell.append(figure);
    return cell;
  }
  figure.textContent = `${number(value)}${suffix}`;
  if (flagged) {
    figure.className = flagClass;
    const note = document.createElement("span");
    note.className = "visually-hidden";
    note.textContent = ` (${flagText})`;
    cell.append(figure, note);
  } else {
    cell.append(figure);
  }
  return cell;
}

function subjectRow(subject, rules) {
  const row = document.createElement("tr");
  const name = document.createElement("th");
  name.scope = "row";
  name.textContent = subject.name;
  const below = `below ${rules.threshold}%`;
  const marks = subject.absent
    ? figureCell(0, "", true, "figure-fail", "absent")
    : figureCell(subject.marks, `/${rules.midsemMax}`, subject.fail, "figure-fail", "below the pass mark");
  if (subject.absent) marks.querySelector("span").textContent = "AB";
  row.append(
    name,
    figureCell(subject.theory, "%", subject.theoryShort, "figure-short", below),
    figureCell(subject.practical, "%", subject.practicalShort, "figure-short", below),
    marks,
  );
  return row;
}

export function renderStudent(dialog, student, rules) {
  slot(dialog, "name").textContent = student.name;
  slot(dialog, "enrollment").textContent = student.enrollment;
  const badge = slot(dialog, "badge");
  badge.className = `badge badge--${student.badge.replace("_", "-")}`;
  badge.textContent = BADGE_LABELS[student.badge] ?? student.badge;
  slot(dialog, "parent").textContent = student.parent || "Not given";
  const phone = slot(dialog, "phone");
  phone.textContent = student.phoneValid
    ? student.phone
    : `${student.phone || "Missing"} · not a valid mobile number`;
  phone.classList.toggle("figure-fail", !student.phoneValid);
  slot(dialog, "subjects").replaceChildren(
    ...student.subjects.map((subject) => subjectRow(subject, rules)),
  );
}

// The note marker the server put in each "withNote" message; see services/messaging/previews.py.
export const NOTE_MARKER = "⁣NOTE⁣";

// The message exactly as it will open in WhatsApp, for the preview and the link.
export function messageText(student, language, note = "") {
  const messages = student.messages[language];
  const trimmed = note.trim();
  return trimmed ? messages.withNote.replace(NOTE_MARKER, trimmed) : messages.plain;
}

export function renderMessage(dialog, student, language, note = "") {
  const text = messageText(student, language, note);
  slot(dialog, "message").textContent = text;
  return text;
}
