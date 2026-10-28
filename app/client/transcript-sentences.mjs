// Group display fragments only. Stored ASR evidence and segment IDs stay intact.
function finishesSentence(text) {
  return /(?<!\.)[.!?]["'”’)]*$/.test(text.trim());
}

export function sentenceRows(segments) {
  const rows = [];
  for (const segment of segments) {
    const data = segment.data;
    const last = rows.at(-1);
    const prior = last?.data;
    const display = data.activation_correction?.text ?? data.text;
    const delta = data.captured_at_ms - prior?.last_captured_at_ms;
    const sameVoice = prior && data.attribution === prior.attribution &&
      data.speaker_profile_id === prior.speaker_profile_id &&
      data.speaker_actor_id === prior.speaker_actor_id;
    const joins = prior && data.capture_id && data.capture_id === prior.capture_id &&
      data.capture_revision === prior.capture_revision && sameVoice &&
      !data.provenance?.synthetic && !prior.provenance?.synthetic &&
      Number.isFinite(delta) && delta > 0 && delta <= (data.duration_ms ?? 6000) + 2000 &&
      !finishesSentence(prior.display_text);
    if (joins) {
      prior.text += " " + data.text;
      prior.display_text += " " + display;
      prior.last_captured_at_ms = data.captured_at_ms;
      prior.voice_command = data.voice_command ?? prior.voice_command;
      if (prior.activation_correction || data.activation_correction) {
        prior.activation_correction = { corrected: true, text: prior.display_text };
      }
      last.segment_ids.push(segment.id);
    } else {
      rows.push({ ...segment, segment_ids: [segment.id], data: { ...data,
        display_text: display, last_captured_at_ms: data.captured_at_ms } });
    }
  }
  return rows;
}
