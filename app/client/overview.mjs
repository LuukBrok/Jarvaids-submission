/** Shared overview records, with original transcript citations and explicit retries. */
let last = '';
const el = (tag, cls, text) => { const node = document.createElement(tag); node.className = cls; node.textContent = text; return node; };

export function renderOverview(snapshot, send) {
  const available = snapshot.session.summary_ai?.available;
  document.getElementById('tab-overview').hidden = !available;
  document.getElementById('summary-status').hidden = !available;
  const state = snapshot.records.find(r => r.kind === 'summary_state');
  const works = snapshot.records.filter(r => r.kind === 'summary_work');
  const failed = works.find(r => ['error', 'blocked'].includes(r.data.status));
  const pending = works.filter(r => ['running', 'queued'].includes(r.data.status));
  const topics = snapshot.records.filter(r => r.kind === 'summary_topic');
  const active = snapshot.session.state === 'active';
  const message = !available ? 'Local summaries are not enabled in this server.' : failed ? failed.data.error
    : pending.length ? `Summary is catching up: ${pending.length} ${pending.length === 1 ? 'batch' : 'batches'} remaining.`
    : state?.data.enabled === false ? 'Automatic summaries paused.'
    : `${topics.length} ${topics.length === 1 ? 'topic' : 'topics'}. ${state?.data.buffered_words || 0} words waiting for the next summary batch.`;
  document.getElementById('summary-status').textContent = (available ? (snapshot.session.summary_ai.local ? 'Local summary. ' : 'Cloud summary. ') : '') + message;
  document.getElementById('overview-status').textContent = message;
  document.getElementById('summary-flush').disabled = !available || !active;
  document.getElementById('summary-save').disabled = !available || snapshot.session.state === 'closed';
  const signature = JSON.stringify([topics.map(r => [r.id, r.revision]), works.map(r => [r.id, r.revision]), active]);
  if (document.activeElement?.id !== 'summary-agenda' && document.activeElement?.id !== 'summary-enabled') {
    if (document.getElementById('summary-agenda').dataset.session !== snapshot.session.id) {
      document.getElementById('summary-agenda').value = (state?.data.agenda || []).join('\n');
      document.getElementById('summary-enabled').checked = state?.data.enabled !== false;
      document.getElementById('summary-agenda').dataset.session = snapshot.session.id;
    }
  }
  if (last === signature) return;
  last = signature;
  const root = document.getElementById('overview-topics'); root.replaceChildren();
  if (failed) {
    const button = el('button', 'btn btn-secondary', 'Retry failed summary'); button.type = 'button'; button.disabled = !active;
    button.addEventListener('click', () => send('summary.retry', {work_id: failed.id, expected_revision: failed.revision}).catch(() => {}));
    root.append(button);
  }
  if (!topics.length) root.append(el('p', 't-small', 'Speak or type discussion, then choose Update summary now. Summaries also update automatically after a completed batch.'));
  for (const theme of [...new Set(topics.map(r => r.data.theme))]) {
    const section = el('section', 'rail-section', ''); section.append(el('h3', 't-title', theme));
    for (const topic of topics.filter(r => r.data.theme === theme)) {
      const details = el('details', 'rail-section', '');
      details.append(el('summary', 't-signal', topic.data.title));
      details.append(el('p', 't-meta', 'AI interpretation. Check its evidence and correct the canvas note when needed.'));
      for (const entry of topic.data.entries) {
        details.append(el('p', 't-meta', new Date(entry.started_at * 1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})));
        details.append(el('p', 't-body', entry.summary));
        for (const [key, title] of [['decisions', 'Decision'], ['action_items', 'Action'], ['open_questions', 'Open question']]) {
          for (const row of entry[key]) details.append(el('p', 't-body', `${title}: ${row.text}${row.owner ? ` (${row.owner})` : ''}`));
        }
        const evidence = el('details', '', ''); evidence.append(el('summary', 't-meta', 'Transcript evidence'));
        for (const ref of entry.source_refs) {
          const line = snapshot.records.find(r => r.id === ref.id);
          if (!line) continue;
          const quote = el('button', 'btn btn-quiet', line.data.text); quote.type = 'button';
          quote.addEventListener('click', () => {
            document.getElementById('tab-transcript').click();
            document.getElementById(`seg-${ref.id}`)?.scrollIntoView({block:'center'});
          }); evidence.append(quote);
        }
        details.append(evidence);
      }
      section.append(details);
    }
    root.append(section);
  }
}
