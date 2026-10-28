/**
 * "Add and accept": a facilitator's typed note, added and accepted in one
 * press (docs/specs/2026-10-18-canvas-object-model.md, the review rule).
 *
 * It is one step for the person and two commands for the record, on purpose:
 * `source.text` says who wrote it and `proposal.review` says who accepted it,
 * so the record reads the same as when the two happen minutes apart. A typed
 * note still goes through review; a facilitator just does both at once.
 *
 * The two can fail separately, and the screen must say which happened. If
 * the note was added but not accepted, it is on the canvas waiting for
 * review, and saying "nothing happened" would invite a duplicate. Pure, so
 * each path is tested without a server (tests/canvas-objects-unit.mjs).
 */

/** Runs both commands through `send`. Never throws: the outcome says how far
 * it got. `stage` is "add" (nothing was added), "accept" (added, not
 * accepted) or "done". */
export async function addAndAccept(send, text) {
  let added;
  try { added = await send("source.text", { text }); }
  catch (error) { return { stage: "add", error }; }
  const proposal = added?.proposal;
  if (!proposal?.id) return { stage: "accept", added, error: null };
  try {
    const result = await send("proposal.review", { proposal_id: proposal.id,
      expected_revision: proposal.revision, decision: "accept" });
    return { stage: "done", added, item: result?.item ?? null };
  } catch (error) {
    return { stage: "accept", added, error };
  }
}

const uncertain = error => error?.outcome === "unknown" || error?.cause?.outcome === "unknown";

/** What the banner says afterwards, or null when `send` has already said it
 * (nothing was added, and its own banner names the reason). */
export function addAndAcceptMessage(outcome, describe = e => String(e?.message ?? e)) {
  if (outcome.stage === "add") return null;
  if (outcome.stage === "done") {
    return { kind: "note", text: "Added and accepted. The record names you as the person who accepted it." };
  }
  if (uncertain(outcome.error)) {
    return { kind: "problem", text: "Added to the canvas. The server may or may not have accepted it, so nothing was " +
      "retried. Check Review before accepting it again." };
  }
  const reason = outcome.error ? describe(outcome.error).trim().replace(/([^.])$/, "$1.") : "The server did not say which note it added.";
  return { kind: "problem", text: `Added to the canvas, but it could not be accepted: ${reason} It is waiting for review.` };
}
