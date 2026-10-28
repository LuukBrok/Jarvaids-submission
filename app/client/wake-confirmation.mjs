/** Acoustic candidates cannot ring: require new, non-synthetic spoken evidence. */
export class WakeConfirmation {
  constructor(onConfirmed) { this.onConfirmed = onConfirmed; this.seen = new Set(); }
  begin(snapshot) { this.seen = new Set(snapshot.records.filter(r => r.kind === 'transcript_segment').map(r => r.id)); }
  update(snapshot, listening) {
    for (const record of snapshot.records) {
      if (record.kind !== 'transcript_segment' || this.seen.has(record.id)) continue;
      this.seen.add(record.id);
      const d = record.data, command = d.voice_command;
      if (!listening || d.status !== 'final' || d.input_method === 'typed' || d.provenance?.synthetic ||
          !command || command.activation_segment_id || command.phrase !== 'Hey Jarvaids') continue;
      this.onConfirmed(record);
    }
  }
}
