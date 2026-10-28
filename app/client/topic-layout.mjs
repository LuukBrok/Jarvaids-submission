/** Presentation only: summary themes organise a snapshot without changing it. */
export const TOPIC_TONES = ['yellow', 'lilac', 'mint', 'periwinkle', 'coral'];
export const TOPIC_CARD_WIDTH = 224;
const clean = value => String(value || '').normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
const STOP = new Set('the a an and or to of for in on with we our this that it is are be was as by from their they will should can have has said not'.split(' '));
const words = value => clean(value).split(' ').filter(w => w.length > 2 && !STOP.has(w));

export function topicGroups(snapshot, items) {
  const records = snapshot?.records || [], topics = records.filter(r => r.kind === 'summary_topic');
  const agenda = records.find(r => r.kind === 'summary_state')?.data.agenda || [];
  const labels = [...new Set([...agenda, ...topics.map(t => t.data.theme)].filter(Boolean))];
  const ensure = label => { if (!labels.includes(label)) labels.push(label); return label; };
  const named = (pattern, fallback) => ensure(labels.find(label => pattern.test(clean(label))) || fallback);
  const types = new Map(topics.map(t => [t.id, t.data.theme]));
  const noteThemes = new Map(topics.filter(t => t.data.note_id).map(t => [t.data.note_id, t.data.theme]));
  const sourceThemes = new Map(records.filter(r => r.kind === 'source' && types.has(r.data.summary_topic_id)).map(r => [r.id, types.get(r.data.summary_topic_id)]));
  const vocabulary = new Map();
  for (const topic of topics) {
    const theme = topic.data.theme, bag = vocabulary.get(theme) || new Map();
    for (const [text, weight] of [[topic.data.title, 4], [topic.data.description, 2], [(topic.data.entries || []).map(e => e.summary).join(' '), 1]])
      for (const word of new Set(words(text))) bag.set(word, (bag.get(word) || 0) + weight);
    vocabulary.set(theme, bag);
  }
  const parked = new Set(records.filter(r => r.kind === 'item' && r.data.item_kind === 'section' && r.data.title === 'Parked' && r.data.made_by_hand)
    .flatMap(r => r.data.member_ids || []));
  const groups = new Map(), associations = new Map();
  for (const item of items) {
    if (parked.has(item.id) || item.data.state === 'cancelled') continue;
    let label = types.get(item.data.summary_topic_id) || noteThemes.get(item.id);
    let basis = 'summary';
    if (!label) label = (item.data.refs || []).map(ref => sourceThemes.get(ref.id)).find(Boolean);
    if (!label) {
      basis = 'suggested';
      const text = clean(item.data.text || item.data.title || item.data.question);
      if (item.kind === 'poll') label = named(/concept choice|vot|decision/, 'Concept choice');
      else if (item.data.document_type === 'requirements') label = named(/requirement|criteria|wish/, 'Requirements');
      else if (['todo', 'calendar'].includes(item.data.document_type) || /^(interview|check|sketch|test|prepare|schedule|organise)\b/.test(text))
        label = named(/task|calendar|planning|action/, 'Tasks and calendar');
      else if (/\b(step free|free entry|mains|electrical|furniture|smartphone|paper route|welcome desk|requirement)\b/.test(text))
        label = named(/requirement|criteria|wish/, 'Requirements');
      else if (/\b(pop up|mobile repair|permanent repair|concept|alternative|vote|poll)\b/.test(text) || text === 'decision')
        label = named(/concept choice|vot|decision/, 'Concept choice');
      else if (/\b(keep broken|motivation|beginners|purpose|learning|learn)\b/.test(text))
        label = named(/purpose|motivation|goal/, 'Purpose and concepts');
      else {
        const scores = [...vocabulary].map(([theme, bag]) => [theme, [...new Set(words(text))].reduce((n, w) => n + Math.min(4, bag.get(w) || 0), 0)])
          .sort((a, b) => b[1] - a[1]);
        label = scores[0]?.[1] >= 3 ? scores[0][0] : named(/physical notes/, 'Needs sorting');
      }
    }
    ensure(label);
    const association = {label, basis}; associations.set(item.id, association);
    if (!groups.has(label)) groups.set(label, {id: `topic-${clean(label).replaceAll(' ', '-')}`, label, tone: TOPIC_TONES[labels.indexOf(label) % TOPIC_TONES.length], items: []});
    groups.get(label).items.push(item);
  }
  return {groups: labels.filter(label => groups.has(label)).map(label => groups.get(label)), associations};
}

/** Choose a balanced grid by the fit it actually achieves in this viewport. */
export function layoutTopicGroups(groups, sizes, viewport = {width: 1200, height: 700}) {
  const gap = 16, gutter = 32, pad = 16, header = 64;
  let best = null;
  for (let columns = 1; columns <= Math.min(3, groups.length); columns++) for (let cards = 2; cards <= 4; cards++) {
    const width = cards * TOPIC_CARD_WIDTH + (cards - 1) * gap + pad * 2;
    if (groups.some(g => g.items.some(item => (sizes.get(item.id)?.w || TOPIC_CARD_WIDTH) > width - pad * 2 + 1))) continue;
    const blocks = groups.map(group => {
      let column = 0, y = header, rowHeight = 0;
      const placements = [];
      for (const item of group.items) {
        const size = sizes.get(item.id) || {w: TOPIC_CARD_WIDTH, h: 100};
        const span = Math.max(1, Math.ceil((size.w + gap) / (TOPIC_CARD_WIDTH + gap)));
        if (column && column + span > cards) {y += rowHeight + gap; column = 0; rowHeight = 0;}
        placements.push({id: item.id, x: pad + column * (TOPIC_CARD_WIDTH + gap), y, w: size.w, h: size.h});
        column += span; rowHeight = Math.max(rowHeight, size.h);
        if (column >= cards) {y += rowHeight + gap; column = 0; rowHeight = 0;}
      }
      return {...group, w: width, h: y + rowHeight + pad, placements};
    });
    const bottoms = Array(columns).fill(0), placed = [];
    for (const block of [...blocks].sort((a, b) => b.h - a.h || groups.findIndex(g => g.id === a.id) - groups.findIndex(g => g.id === b.id))) {
      const col = bottoms.indexOf(Math.min(...bottoms)), x = col * (width + gutter), y = bottoms[col];
      placed.push({...block, x, y, placements: block.placements.map(p => ({...p, x: p.x + x, y: p.y + y}))});
      bottoms[col] = y + block.h + gutter;
    }
    const bounds = {x: 0, y: 0, w: columns * width + (columns - 1) * gutter, h: Math.max(...bottoms) - gutter};
    const scale = Math.min((viewport.width - 96) / bounds.w, (viewport.height - 96) / bounds.h);
    if (!best || scale > best.scale) best = {groups: placed, bounds, scale, columns, cards};
  }
  return best || {groups: [], bounds: {x:0,y:0,w:1,h:1}, scale:1, columns:1, cards:2};
}
