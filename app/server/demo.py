"""Exercise the running HTTP API with synthetic data; never prints credentials."""
import argparse
import base64
import json
import secrets
import struct
import time
from urllib.error import HTTPError
from urllib.request import Request, ProxyHandler, build_opener
import zlib


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:3000');args=parser.parse_args()
    opener=build_opener(ProxyHandler({}));token=secrets.token_urlsafe(32);sid=secrets.token_hex(16)
    def call(method,path,body=None,key=None):
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
        if key:headers['X-Request-ID']=key
        req=Request(args.url+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method)
        try:
            with opener.open(req,timeout=10) as response:return json.loads(response.read())
        except HTTPError as e:
            payload=json.loads(e.read());raise RuntimeError(payload['error']['code']) from None
    prefix=f'/api/sessions/{sid}'
    def command(op,payload,key=None):
        body={'operation':op,'payload':dict(payload)}
        if op in ('session.activate','session.close'):
            snapshot=call('GET',prefix)
            body['payload']['expected_session_revision']=snapshot['session']['revision']
            if op=='session.close':body['control_sequence']=snapshot['next_control_sequence']
        return call('POST',prefix+'/commands',body,key or secrets.token_hex(16))
    health=call('GET','/health');assert health['adapter']=='fixture' and not health['live_ocr']
    call('POST','/api/sessions',{'session_id':sid,'owner_token':token,'owner_name':'Synthetic owner','title':'Synthetic backend demo'})
    try:
        command('consent.acknowledge',{'policy_version':1});command('session.activate',{'policy_version':1})
        key=secrets.token_hex(16);created=command('source.text',{'text':'Keep source evidence attached.'},key)
        assert command('source.text',{'text':'Keep source evidence attached.'},key)['replayed']
        p=created['result']['proposal']
        item=command('proposal.review',{'proposal_id':p['id'],'expected_revision':p['revision'],'decision':'accept'})['result']['item']
        command('item.edit',{'item_id':item['id'],'expected_revision':1,'text':'Keep reviewed source evidence attached.','refs':item['data']['refs']})
        command('item.undo',{'item_id':item['id'],'expected_revision':2,'restore_revision':1})
        def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
        image=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\xff\xff\xff'))+chunk(b'IEND',b'')
        source=command('source.image',{'mime':'image/png','base64':base64.b64encode(image).decode(),
           'regions':[{'id':'demo_region','box':[0,0,1,1]}]})['result']
        job=command('extraction.queue',{'source_id':source['id'],'expected_revision':1})['result']
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            current=call('GET',prefix+'/records/'+job['id'])
            if current['data']['status'] not in ('queued','running'):break
            time.sleep(.1)
        assert current['data']['status']=='succeeded'
        proposal=call('GET',prefix+'/records/'+current['data']['proposal_ids'][0])
        assert proposal['data']['synthetic'] and proposal['data']['origin']=='fixture'
        export=command('export.create',{'include_unresolved':True})['result']
        assert export['data']['manifest']['unresolved_count']==1
        command('session.close',{})
        print('PASS: session agreement, typed review, retry, edit/undo, image fixture job, labelled export and close.')
    finally:
        receipt=call('DELETE',prefix);assert receipt['state']=='deleted'
        assert call('GET',prefix)['state']=='deleted'
        print('PASS: demonstration session content deleted. No model calls or credentials logged.')


if __name__=='__main__':main()
