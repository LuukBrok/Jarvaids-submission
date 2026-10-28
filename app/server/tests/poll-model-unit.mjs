import test from "node:test";
import assert from "node:assert/strict";
import { pollModel } from "../../client/polls.mjs";

test("one current ballot per voice, withdrawals, nonvoters and uncertainty stay distinct", () => {
  const poll = { id: "poll", data: { options: [{ id: "yes", label: "Yes" }, { id: "no", label: "No" }] } };
  const snapshot = { records: [
    ...["a", "b", "c"].map(id => ({ id, kind: "speaker_profile", data: { name: id } })),
    { kind: "poll_ballot", data: { poll_id: "poll", speaker_profile_id: "a", option_id: "yes" } },
    { kind: "poll_ballot", data: { poll_id: "poll", speaker_profile_id: "b", option_id: null } },
    { kind: "poll_work", data: { poll_id: "poll", status: "clarify" } },
    { kind: "poll_work", data: { poll_id: "poll", status: "queued" } },
    { kind: "poll_ballot", data: { poll_id: "other", speaker_profile_id: "c", option_id: "no" } },
  ] };
  const view = pollModel(snapshot, poll);
  assert.deepEqual(view.options.map(o => o.voters.length), [1, 0]);
  assert.equal(view.notVoted, 2);
  assert.equal(view.voted, 1);
  assert.equal(view.unresolved.length, 1);
  assert.equal(view.pending.length, 1);
});
