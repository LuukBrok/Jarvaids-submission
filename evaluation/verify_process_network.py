"""Structural checks for the process documentation; not product integration tests."""
from pathlib import Path
from collections import Counter, deque
from html.parser import HTMLParser
import json, re, subprocess, sys

root=Path(__file__).resolve().parents[1]
docs=root/'deliverables/documentation'
data=json.loads((docs/'process-network.json').read_text(encoding='utf-8'))
nodes={n['id']:n for n in data['nodes']}
assert len(nodes)==len(data['nodes']), 'Duplicate node IDs'
required=['label','lane','scope','owner','input','output','guard','failure','measure','issue']
for n in nodes.values():
    assert all(isinstance(n.get(k),str) and n[k].strip() for k in required),n
    assert n['scope'] in ['core','extension']
types={'flow','dependency','feedback','control','lifecycle','observation'}
triples=[]
for e in data['edges']:
    assert e['source'] in nodes and e['target'] in nodes,e
    assert e['kind'] in types and e['label'],e
    triples.append((e['source'],e['target'],e['kind'],e['label']))
assert len(triples)==len(set(triples)), 'Duplicate edge record'
pairs={(e['source'],e['target']) for e in data['edges']}
for route in data['routes']:
    assert all(n in nodes for n in route['nodes']),route['id']
    for a,b in zip(route['nodes'],route['nodes'][1:]): assert (a,b) in pairs,(route['id'],a,b)
seen={'S01'}
while True:
    new=seen|{b for a,b in pairs if a in seen}
    if new==seen:break
    seen=new
assert seen==set(nodes),'Unreachable nodes: '+str(set(nodes)-seen)
report=(root/'evaluation/process-deep-dive.md').read_text(encoding='utf-8')
issues=set(re.findall(r'^### (F\d\d) ',report,re.M))
assert issues=={f'F{i:02}' for i in range(1,20)}
assert all(n['issue'] in issues for n in nodes.values())
for section in re.split(r'^### F\d\d ',report,flags=re.M)[1:]:
    assert all(f'**{letter} —' in section for letter in ['A','B','C'])
    assert '**Recommend:**' in section
subprocess.run([sys.executable,str(docs/'build_process_network.py')],check=True)
first=(docs/'process-network.html').read_bytes()
subprocess.run([sys.executable,str(docs/'build_process_network.py')],check=True,stdout=subprocess.DEVNULL)
assert first==(docs/'process-network.html').read_bytes(),'Non-deterministic build'
class Parse(HTMLParser):
    def __init__(self): super().__init__();self.ids=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])
p=Parse();text=first.decode('utf-8');p.feed(text)
assert len(p.ids)==len(set(p.ids)),'Duplicate HTML IDs'
for link in p.links:
    if link.startswith('#'):assert link[1:] in p.ids,link
    elif not re.match(r'\w+:',link):assert (docs/link).exists(),link
assert '/*NETWORK_DATA*/' not in text and '<!--CATALOG-->' not in text
assert all('record-'+n in p.ids for n in nodes),'Incomplete no-JS catalog'
print(f"PASS: {len(nodes)} node contracts, {len(data['edges'])} edges, {len(data['routes'])} continuous routes; all nodes reachable")
print('PASS: 19 findings each have A/B/C options and a recommendation; all node flaw references resolve')
print('PASS: deterministic HTML, unique IDs, complete fallback catalog and valid static links')
print('Scope counts:',dict(Counter(n['scope'] for n in nodes.values())))
