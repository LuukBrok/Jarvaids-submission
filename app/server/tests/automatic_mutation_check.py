"""Named automatic-intake guards; crashes and import errors never count."""
from mutation_runner import check_multi_target

MUTANTS = [
    ('automatic-result-capacity','service.py',
     'len(output.notes)*(2 if self.automatic_workspace else 1)',
     'len(output.notes)', 'test_automatic_photo_capacity_is_terminal_and_never_partially_applied'),
    ('startup-source-freshness','service.py',
     "                        self._refs(c,s['id'],d['refs'])",
     '                        pass','test_startup_never_applies_changed_source_references'),
    ('detected-boxes-parent','service.py',
     "                    regions([{'id':note['region_id'],'box':note.get('box')}])",
     '                    pass', 'test_parent_rejects_invalid_detection_even_if_adapter_omits_validation'),
    ('detection-identities','claude_extractor.py',
     "            if answered: regions([{'id':n['region_id'],'box':n['box']} for n in answered])",
     '            pass', 'test_detector_rejects_duplicate_ids_and_more_than_sixty_notes'),
    ('closing-drains-pending','polls.py',
     "        if any(w['data']['status'] in PENDING for w in self._poll_work(c,s['id'],poll['id'])): return poll",
     '        pass','test_closing_drains_queued_votes_before_finishing'),
]

if __name__=='__main__':
    raise SystemExit(check_multi_target(MUTANTS,'test_automatic_workspace.py',60,'automatic','automatic'))
