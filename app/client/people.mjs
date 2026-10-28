/**
 * People: who is here, who has agreed, and who may do what (F02 to F07, F13).
 *
 * The same rows appear on the agreement gate and in the People panel, so the
 * room can always see whose agreement capture is waiting for. Withdrawing is
 * one press with no confirmation, because stopping capture must never be
 * harder than starting it.
 */
import { newToken } from "../server/client.mjs";
import { renderSpeakers } from "./speakers.mjs";

export function agreed(s, m) {
  return m.consent_version === s.session.policy_version;
}

export function waitingFor(s) {
  return s.members.filter(m => !agreed(s, m));
}

/** "Sam", "Sam and Jo", "Sam, Jo and Ali". */
export function names(list) {
  const n = list.map(m => m.name);
  return n.length <= 1 ? (n[0] ?? "") : `${n.slice(0, -1).join(", ")} and ${n.at(-1)}`;
}

// ------------------------------------------------------------ people colours
//
// Each person has one colour, chosen by their place in `snapshot.members`,
// which is join order. The same colour marks them in People, in the
// transcript, on a quote note and in the header, so a person is recognisable
// across the screen without reading a name. Ten tokens, --person-1 to
// --person-10: the five accents, then their -deep (tokens.css). Eight people
// is the server's limit, so nobody shares a colour in practice; the tenth
// wraps to the first.

const ACCENTS = ["lilac", "mint", "periwinkle", "coral", "yellow"];

/** A member's place in join order, or -1 when the id is not a member. */
export function personIndex(snapshot, actorId) {
  if (actorId == null) return -1;
  return snapshot?.members?.findIndex(m => m.id === actorId) ?? -1;
}

/** The fill for a person's circle: `var(--person-N)`, or null for nobody. */
export function personColour(index) {
  return index >= 0 ? `var(--person-${(index % 10) + 1})` : null;
}

/** The ink for a person's name: their accent's -deep, which is legible as
 * text on the ground where the full accent is not (DESIGN.md 2.2). */
export function personInk(index) {
  return index >= 0 ? `var(--${ACCENTS[index % 5]}-deep)` : null;
}

/** HH:MM, or HH:MM:SS, in the device's time, from seconds since 1970. Mono
 * timestamps everywhere in the rail come from here. Empty for no time. */
export function clockTime(seconds, { withSeconds = false } = {}) {
  if (seconds == null || !Number.isFinite(Number(seconds))) return "";
  const d = new Date(Number(seconds) * 1000);
  const two = n => String(n).padStart(2, "0");
  return `${two(d.getHours())}:${two(d.getMinutes())}` + (withSeconds ? `:${two(d.getSeconds())}` : "");
}

/** When a person joined the record: the time they agreed, or "not yet". */
export function joinTime(member) {
  return member?.agreed_at ? clockTime(member.agreed_at) : "not yet";
}

export function createPeople(ctx) {
  const { app, $, show, send, attention, render, button, confirm, clock } = ctx;

  /** Agreed, Withdrew HH:MM, or Waiting. The agreement time itself is the
   * row's mono time, so the mark does not repeat it. */
  function agreementMark(s, m) {
    const span = document.createElement("span");
    if (agreed(s, m)) {
      span.className = "status st-accepted agreement";
      span.innerHTML = '<i class="glyph glyph-accepted" aria-hidden="true"></i>';
      span.append(word("Agreed"));
    } else if (m.withdrawn_at) {
      span.className = "status st-off agreement";
      span.innerHTML = '<i class="glyph glyph-off" aria-hidden="true"></i>';
      span.append(word(`Withdrew ${clock(m.withdrawn_at)}`));
    } else {
      span.className = "status st-waiting agreement";
      span.innerHTML = '<i class="glyph glyph-waiting" aria-hidden="true"></i>';
      span.append(word("Waiting"));
    }
    return span;
  }

  function word(text) {
    const w = document.createElement("span");
    w.className = "word";
    w.textContent = text;
    return w;
  }

  function personRow(s, m, { manage }) {
    const me = m.id === s.actor_id;
    const li = document.createElement("li");
    li.className = "person";
    li.dataset.actorId = m.id;
    const index = personIndex(s, m.id);
    const dot = document.createElement("span");
    dot.className = "person-dot";
    dot.setAttribute("aria-hidden", "true");
    dot.style.setProperty("--person", personColour(index));
    const who = document.createElement("span");
    who.className = "person-who";
    const name = document.createElement("span");
    name.className = "person-name";
    name.textContent = m.name + (me ? " (you)" : "");
    const facts = document.createElement("span");
    facts.className = "person-facts";
    const role = document.createElement("span");
    role.className = "t-small role";
    role.textContent = m.role === "facilitator" ? "Facilitator" : m.role === "viewer" ? "Viewer" : "Participant";
    const time = document.createElement("time");
    time.className = "t-mono person-time";
    time.textContent = joinTime(m);
    if (m.agreed_at) {
      time.dateTime = new Date(m.agreed_at * 1000).toISOString();
      time.title = `Agreed at ${clockTime(m.agreed_at)}`;
    }
    facts.append(role, time);
    who.append(name, facts);
    li.append(dot, who, agreementMark(s, m));
    if (!manage) return li;

    const actions = document.createElement("span");
    actions.className = "person-actions";
    const closed = s.session.state === "closed";
    if (me && !closed) {
      if (agreed(s, m)) {
        actions.append(button("Withdraw agreement", "btn-quiet btn-sm", () => withdraw()));
      } else {
        actions.append(button("Agree again", "btn-secondary btn-sm", () =>
          send("consent.acknowledge", { policy_version: s.session.policy_version })));
      }
    }
    const iFacilitate = s.members.find(x => x.id === s.actor_id)?.role === "facilitator";
    if (iFacilitate && !me && !closed) {
      const next = m.role === "facilitator" ? "participant" : "facilitator";
      actions.append(button(next === "facilitator" ? "Make facilitator" : "Make participant", "btn-quiet btn-sm", () =>
        send("participant.role", { actor_id: m.id, role: next, expected_roster_revision: s.session.roster_revision })));
      actions.append(button("Remove", "btn-danger btn-sm", async () => {
        const ok = await confirm({ title: `Remove ${m.name}?`,
          text: `${m.name} leaves the session at once and cannot rejoin with this device. What they added stays, with their name on it.`,
          detail: "To let them back in, send a new invitation.", action: "Remove", danger: true });
        if (ok) await send("participant.remove", { actor_id: m.id, expected_roster_revision: s.session.roster_revision });
      }));
    }
    if (actions.childElementCount) li.append(actions);
    return li;
  }

  async function withdraw() {
    ctx.stopListening();
    await send("consent.withdraw", {});
    attention("You withdrew your agreement, so capture stopped for the room. Agree again to let it resume.", "note");
  }

  function renderRows(s, box, options) {
    box.textContent = "";
    for (const m of s.members) box.append(personRow(s, m, options));
  }

  function renderPeople(s) {
    renderRows(s, $("people-rows"), { manage: true });
    const iFacilitate = s.members.find(x => x.id === s.actor_id)?.role === "facilitator";
    show($("invite-section"), iFacilitate && s.session.state !== "closed");
    renderSpeakers(s);
    const active = s.session.state === "active";
    $("speaker-reason").textContent = active ? "" : "Voices can be recorded while capture is running.";
  }

  /** The roster revision the last invitation was sent against. An
   * invitation moves the roster on, and the screen only hears of it at the
   * next poll, so a second press within that second used to be refused
   * ("Refresh the roster before changing membership"). The second press
   * waits for the poll instead, at most three seconds. */
  let invitedAt = null;

  async function invite() {
    for (let waited = 0; invitedAt != null && app.snapshot?.session.roster_revision === invitedAt && waited < 3000; waited += 100) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    const s = app.snapshot;
    const invitation = newToken();
    try {
      await send("participant.invite", { invitation,
        expected_roster_revision: s.session.roster_revision, role: "participant" });
    } catch { show($("invite-created"), false); return; }
    invitedAt = s.session.roster_revision;
    // One string, because three fields read off a projector is three mistakes.
    // Shown only once the server has the invitation: a code that was never
    // issued would be refused at the door.
    $("invite-code").textContent = `${s.session.id}.${s.session.policy_version}.${invitation}`;
    show($("invite-created"), true);
  }

  async function copyInvite() {
    const code = $("invite-code").textContent;
    try { await navigator.clipboard.writeText(code); attention("Invitation copied. Send it to one person.", "note"); }
    catch {
      const range = document.createRange(); range.selectNodeContents($("invite-code"));
      const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(range);
      attention("Copy the selected code, then send it to one person.", "note");
    }
  }

  return { renderRows, renderPeople, invite, copyInvite, withdraw, agreementMark };
}
