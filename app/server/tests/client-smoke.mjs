/** Run against the CLI server: node tests/client-smoke.mjs http://127.0.0.1:3000 */
import assert from "node:assert/strict";
import {GenAIClient, ApiError, newId, newToken} from "../client.mjs";

const client = new GenAIClient({baseUrl: process.argv[2], sessionId: newId(), token: newToken()});
await client.create({ownerName: "Synthetic JS owner", title: "Client smoke"});
try {
  await client.submit(client.intent("consent.acknowledge", {policy_version: 1}));
  await client.submit(client.intent("session.activate", {policy_version: 1, expected_session_revision: (await client.snapshot()).session.revision}));
  const payload = {text: "JS integration fixture"};
  const intent = client.intent("source.text", payload);
  payload.text = "Changed local object must not change the retained intent";
  const created = await client.submit(intent);
  assert.equal(created.result.source.data.text, "JS integration fixture");
  assert.equal((await client.submit(intent)).replayed, true);
  const proposal = created.result.proposal;
  const cursor = (await client.snapshot()).session.seq;
  const accepted = await client.submit(client.intent("proposal.review", {
    proposal_id: proposal.id, expected_revision: proposal.revision, decision: "accept",
  }));
  const delta = await client.delta(cursor);
  const changed = delta.resync_required ? await client.snapshot() : delta;
  assert.ok(changed.records.some(record => record.id === accepted.result.item.id));
  if (!delta.resync_required) assert.equal(changed.records.length, 2);
  assert.equal(changed.session.seq, accepted.seq);
  assert.ok(Number.isInteger(changed.next_control_sequence));
  await assert.rejects(client.submit(client.intent("item.edit", {
    item_id: accepted.result.item.id, expected_revision: 99, text: "Conflict",
    refs: accepted.result.item.data.refs,
  })), e => e instanceof ApiError && e.status === 409 && e.code === "stale_revision");
  const exported = await client.submit(client.intent("export.create", {include_unresolved: false}));
  assert.match(await client.export(exported.result.id, "markdown"), /JS integration fixture/);
  assert.ok((await client.events()).events.length > 0);
  assert.equal((await client.record(accepted.result.item.id)).data.status, "accepted");
  assert.equal((await client.snapshot()).session.state, "active");
  console.log("PASS: JS client creation, immutable retry intent, review, conflict, events, export and snapshot.");
} finally {
  assert.equal((await client.delete()).state, "deleted");
  console.log("PASS: JS smoke session deleted.");
}
