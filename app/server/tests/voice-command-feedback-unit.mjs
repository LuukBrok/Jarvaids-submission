import test from 'node:test';
import assert from 'node:assert/strict';
import { commandFeedback } from '../voice-command-feedback.mjs';

test('a configured summary provider points to real Overview progress', () => {
  assert.equal(commandFeedback({status:'recognised',intent:'summary'},null,null,true,true),
    'Summary update requested. Follow its progress in Overview.');
});

test('all eight recognised intents have distinct visible feedback', () => {
  const labels = {summary:'summary', visualisation:'visualisation', comparison:'comparison',
    voting:'voting list', suggestions:'suggestions', todo:'to-do list',
    requirements:'requirements or wishes list', planning:'agenda or schedule'};
  for (const [intent, label] of Object.entries(labels)) {
    const message = commandFeedback({status:'recognised', intent});
    assert.equal(message, `Provisional command: ${label} requested. Generation is not connected yet.`);
  }
});

test('unknown or incomplete commands give feedback without claiming recognition', () => {
  assert.match(commandFeedback({status:'unsupported', command:'delete everything'}), /Command not recognised/);
  assert.match(commandFeedback({status:'recognised', intent:'unknown', command:'unknown'}), /Command not recognised/);
  assert.match(commandFeedback({status:'incomplete'}), /two transcript lines can form one request/);
  assert.match(commandFeedback({status:'incomplete',command:'make a'}), /Request unfinished/);
  assert.doesNotMatch(commandFeedback({status:'incomplete',command:'make a'}), /Provisional command/);
  assert.match(commandFeedback(null), /Waiting/);
});
