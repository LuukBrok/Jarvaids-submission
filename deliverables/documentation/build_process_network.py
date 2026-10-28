"""Build a standalone, offline process explorer from process-network.json."""
from pathlib import Path
import json, html, re

HERE = Path(__file__).resolve().parent

def build():
    data = json.loads((HERE / 'process-network.json').read_text(encoding='utf-8'))
    report = (HERE.parents[1] / 'evaluation/process-deep-dive.md').read_text(encoding='utf-8')
    def inline(text):
        text = html.escape(text)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        return re.sub(r'\[([^\]]+)\]\((https://[^ )]+)\)', r'<a href="\2">\1</a>', text)
    data['findings'] = {}
    source = report.split('## Common contracts')[0]
    for match in re.finditer(r'^### (F\d\d) ([^\n]+)\n(.*?)(?=^### F\d\d |\Z)',source,re.M|re.S):
        key,title,body=match.groups()
        paragraphs=[]
        for para in body.strip().split('\n\n'):
            if para.startswith('- '):
                paragraphs.append('<ul>'+''.join('<li>'+inline(v.replace('\n',' '))+'</li>' for v in re.split(r'\n- ',para[2:]))+'</ul>')
            else: paragraphs.append('<p>'+inline(para.replace('\n',' '))+'</p>')
        data['findings'][key]={'title':title,'html':''.join(paragraphs)}
    assert len(data['findings']) == 19
    template = (HERE / 'process-network.template.html').read_text(encoding='utf-8')
    catalog = []
    for n in data['nodes']:
        catalog.append('<details id="record-'+n['id']+'"><summary>'+html.escape(n['id']+' · '+n['label'])+'</summary><dl>'+''.join('<dt>'+html.escape(k.title())+'</dt><dd>'+html.escape(str(n[k]))+'</dd>' for k in ['lane','scope','owner','input','output','guard','failure','measure'])+'</dl></details>')
    encoded=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
    page=template.replace('<!--CATALOG-->','\n'.join(catalog)).replace('/*NETWORK_DATA*/',encoded)
    (HERE / 'process-network.html').write_text(page,encoding='utf-8')
    print(f"Built process-network.html: {len(data['nodes'])} nodes, {len(data['edges'])} directed edges, {len(data['routes'])} walkthroughs")

if __name__ == '__main__': build()
