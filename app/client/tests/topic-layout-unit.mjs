import test from 'node:test';
import assert from 'node:assert/strict';
import {topicGroups, layoutTopicGroups} from '../topic-layout.mjs';

test('summary linkage wins, suggestions are labelled, and source records stay intact', () => {
  const records = [
    {id:'state',kind:'summary_state',data:{agenda:['Purpose and concepts','Physical notes','Requirements','Concept choice','Tasks and calendar']}},
    {id:'topic',kind:'summary_topic',data:{theme:'Physical notes',note_id:'summary',title:'Original wall',entries:[]}},
    {id:'summary',kind:'item',data:{text:'Original wall',summary_topic_id:'topic'}},
    {id:'paper',kind:'item',data:{text:'No mains electrical repairs',colour:{hex:'#' + 'ff00ff'}}},
    {id:'task',kind:'command_document',data:{title:'Tasks',document_type:'todo'}},
    {id:'cancelled',kind:'poll',data:{question:'Old poll',state:'cancelled'}},
    {id:'parked',kind:'item',data:{item_kind:'section',title:'Parked',made_by_hand:true,member_ids:['hidden']}},
    {id:'hidden',kind:'item',data:{text:'Parked idea'}}
  ];
  const before=JSON.stringify(records);
  const result=topicGroups({records},records.filter(r=>['summary','paper','task','hidden','cancelled'].includes(r.id)));
  assert.deepEqual(result.groups.map(g=>g.label),['Physical notes','Requirements','Tasks and calendar']);
  assert.equal(result.associations.get('summary').basis,'summary');
  assert.equal(result.associations.get('paper').basis,'suggested');
  assert.equal(result.associations.get('paper').label,'Requirements');
  assert.equal(new Set(result.groups.map(g=>g.tone)).size,3);
  assert.equal(JSON.stringify(records),before);
});

test('measured cards remain inside their groups with no overlap at both viewports', () => {
  const groups=Array.from({length:5},(_,g)=>({id:`g${g}`,label:`Group ${g}`,items:Array.from({length:g*3+3},(_,n)=>({id:`${g}-${n}`}))}));
  const sizes=new Map(groups.flatMap(g=>g.items.map((r,n)=>[r.id,{w:n===1?464:224,h:n===1?420:100+n*7}])));
  for (const viewport of [{width:1400,height:800},{width:400,height:800}]) {
    const result=layoutTopicGroups(groups,sizes,viewport);
    assert.deepEqual(result,layoutTopicGroups(groups,sizes,viewport));
    const all=result.groups.flatMap(g=>g.placements);
    assert.equal(new Set(all.map(p=>p.id)).size,sizes.size);
    const overlap=(a,b)=>a.x<b.x+b.w&&a.x+a.w>b.x&&a.y<b.y+b.h&&a.y+a.h>b.y;
    for(const g of result.groups) for(const p of g.placements) {
      assert.ok(p.x>=g.x&&p.y>=g.y+64&&p.x+p.w<=g.x+g.w&&p.y+p.h<=g.y+g.h);
      for(const q of all) if(p!==q) assert.equal(overlap(p,q),false,`${p.id} overlaps ${q.id}`);
    }
    assert.ok(result.bounds.w/result.bounds.h<4,'compact canvas rather than a ribbon');
  }
});
