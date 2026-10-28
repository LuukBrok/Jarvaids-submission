"""Bounded local/LAN JSON transport for the prototype, not internet hosting."""
import gzip
import json
import math
import ipaddress
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .validation import Problem, fields, require


MAX_BODY=6*1024*1024
MIN_COMPRESS=1024


def checked_origin(value):
    url=urlsplit(value)
    try:port=url.port
    except ValueError:raise ValueError('Invalid origin port.')
    if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.path or url.query or url.fragment:
        raise ValueError('Use an exact HTTP(S) origin without credentials, path, query or fragment.')
    if value!=f'{url.scheme}://{url.netloc}':raise ValueError('Use an exact origin.')
    return value


def parse_json(raw):
    def object_pairs(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate key')
            result[key]=value
        return result
    def invalid_constant(value):raise ValueError('Nonfinite number')
    # `1e999` is not the literal Infinity, so parse_constant never sees it; it
    # becomes inf here and would otherwise reach the fingerprint as a 500.
    def finite_float(value):
        number=float(value)
        if not math.isfinite(number):raise ValueError('Nonfinite number')
        return number
    # An integer too large for a float makes math.isfinite raise OverflowError
    # in every validator that checks it, which is the same 500 by another road.
    def float_sized_int(value):
        number=int(value)
        float(number)
        return number
    try:
        parsed=json.loads(raw.decode('utf-8'),object_pairs_hook=object_pairs,parse_constant=invalid_constant,
                          parse_float=finite_float,parse_int=float_sized_int)
    except (ValueError,UnicodeDecodeError,RecursionError,OverflowError):
        raise Problem(400,'invalid_json','Request must contain valid UTF-8 JSON without duplicate keys or nonfinite numbers.')
    reject_surrogates(parsed)
    return parsed


# No request this server takes nests deeper than a handful of levels. Before
# Python 3.12, json.loads refused deep nesting with RecursionError; since then
# it parses five thousand levels happily, so the limit is stated here instead
# of borrowed from the interpreter.
MAX_JSON_DEPTH=64


def reject_surrogates(value):
    """Refuse text that cannot be written back out.

    `json.loads` accepts a `\\ud800` escape and hands back a string holding an
    unpaired surrogate. Nothing complains until something encodes it, and the
    first thing that does is the idempotency fingerprint, before any handler or
    validator sees the field. The request died as a 500 with no indication of
    which field was wrong.

    Checked here rather than per field because the fingerprint encodes the whole
    body, including keys and values no validator will ever look at. Iterative
    rather than recursive: the input is untrusted and json.loads already permits
    deeper nesting than a recursive walk would survive. The same walk enforces
    MAX_JSON_DEPTH.
    """
    stack=[(value,1)]
    while stack:
        current,depth=stack.pop()
        if depth>MAX_JSON_DEPTH:
            raise Problem(400,'invalid_json','JSON is nested more deeply than any request needs.')
        if isinstance(current,str):
            if not current.isascii():
                try:current.encode('utf-8')
                except UnicodeEncodeError:
                    raise Problem(400,'invalid_json',
                                  'Text must be valid Unicode without unpaired surrogates.')
        elif isinstance(current,dict):
            stack.extend((item,depth+1) for item in (*current.keys(),*current.values()))
        elif isinstance(current,list):
            stack.extend((item,depth+1) for item in current)


class LocalServer(ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=True

    def __init__(self,address,service,origins=(),advertised_hosts=(),slots=16,idle_timeout=10):
        binding=ipaddress.IPv4Address(address[0])
        if not binding.is_loopback and not advertised_hosts:
            raise ValueError('LAN binding requires explicit advertised hosts.')
        hosts=set(advertised_hosts) | {'127.0.0.1','localhost'}
        if any(not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?',host) or host=='0.0.0.0' for host in hosts):
            raise ValueError('Advertised hosts must be explicit hostnames or IPv4 addresses.')
        self.service=service
        self.origins={checked_origin(value) for value in origins}
        # Both are settable so the bound can be tested. A limit nobody has
        # watched reach its ceiling is a guess, and with keep-alive a slot is
        # now held for a whole connection rather than a single request, so the
        # ceiling is much easier to reach than it was on HTTP/1.0.
        self.slots=threading.BoundedSemaphore(slots)
        self.slot_count=slots
        self.idle_timeout=idle_timeout
        super().__init__(address,Handler)
        self.allowed_hosts={f'{host}:{self.server_port}' for host in hosts}
        self.origins.update(f'http://{host}' for host in self.allowed_hosts)

    def process_request(self,request,client_address):
        if not self.slots.acquire(blocking=False):
            try:request.sendall(b'HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
            finally:self.shutdown_request(request)
            return
        try:super().process_request(request,client_address)
        except BaseException:
            self.slots.release();raise

    def process_request_thread(self,request,client_address):
        try:super().process_request_thread(request,client_address)
        finally:self.slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version='Jarvaids-local/0.1'
    sys_version=''
    # Keep-alive. A review client polls events and refetches a handful of
    # records per acceptance, and on HTTP/1.0 each of those paid a fresh
    # connection. The 10 second socket timeout below is what stops an idle
    # connection holding one of the sixteen slots indefinitely.
    protocol_version='HTTP/1.1'

    def setup(self):
        super().setup();self.connection.settimeout(self.server.idle_timeout)
        self.consumed=False

    def handle_one_request(self):
        # Per request, not per connection: setup() runs once for the whole
        # connection, so a flag set there stays set for every later request on
        # it and the drain below silently stops happening.
        self.consumed=False
        super().handle_one_request()

    def log_message(self,*args):
        # Paths, query strings and bodies may contain source material or credentials.
        pass

    def _send(self,status,value,content_type='application/json; charset=utf-8',filename=None):
        self._drain()
        payload=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False,allow_nan=False).encode('utf-8')
        encoding=None
        if len(payload)>=MIN_COMPRESS and 'gzip' in self.headers.get('Accept-Encoding',''):
            # mtime=0 so the same payload always compresses to the same bytes,
            # which keeps the measurement in tests/measure_sync.py reproducible.
            compressed=gzip.compress(payload,mtime=0)
            if len(compressed)<len(payload):payload,encoding=compressed,'gzip'
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        if encoding:self.send_header('Content-Encoding',encoding)
        self.send_header('Vary','Accept-Encoding')
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'none'; sandbox")
        origin=self.headers.get('Origin')
        if origin in self.server.origins:
            self.send_header('Access-Control-Allow-Origin',origin)
            self.send_header('Vary','Origin')
            self.send_header('Access-Control-Expose-Headers','Content-Disposition')
        if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.end_headers()
        try:self.wfile.write(payload)
        except (BrokenPipeError,ConnectionResetError):pass

    def _drain(self):
        """Read a body this request never looked at, before answering.

        Only matters now that connections are reused: a POST to an unknown route
        is answered 404 without reading its body, and those bytes would then be
        parsed as the start of the next request on the same connection. A body
        too large to be worth draining closes the connection instead.
        """
        if self.consumed:return
        length=self.headers.get('Content-Length','')
        if not length.isdigit() or int(length)==0:return
        self.consumed=True
        remaining=int(length)
        if remaining>MAX_BODY:
            self.close_connection=True;return
        while remaining>0:
            chunk=self.rfile.read(min(remaining,65536))
            if not chunk:
                self.close_connection=True;return
            remaining-=len(chunk)

    def _boundary(self):
        require(self.headers.get('Host') in self.server.allowed_hosts,'invalid_host','Use a configured host and port.',403)
        origin=self.headers.get('Origin')
        require(origin is None or origin in self.server.origins,'origin_denied','This browser origin is not allowed.',403)
        require(not self.headers.get('Transfer-Encoding'),'unsupported_encoding','Chunked request bodies are not supported.',400)

    def _body(self,limit=MAX_BODY):
        require(self.headers.get_content_type()=='application/json','unsupported_content_type','Use application/json.',415)
        lengths=self.headers.get_all('Content-Length') or []
        require(len(lengths)==1 and lengths[0].isdigit(),'invalid_length','Supply one valid Content-Length.',400)
        size=int(lengths[0]);require(0<size<=limit,'body_too_large','Request exceeds the JSON size limit.',413)
        raw=self.rfile.read(size);self.consumed=True
        require(len(raw)==size,'incomplete_body','Request body was incomplete.',400)
        return parse_json(raw)

    def _token(self):
        auth=self.headers.get('Authorization','')
        require(auth.startswith('Bearer '),'unauthorized','Use an Authorization: Bearer credential.',401)
        return auth[7:]

    def do_OPTIONS(self):
        try:
            self._boundary()
            self.send_response(204)
            origin=self.headers.get('Origin')
            if origin in self.server.origins:self.send_header('Access-Control-Allow-Origin',origin)
            self.send_header('Vary','Origin')
            self.send_header('Access-Control-Allow-Methods','GET, POST, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers','Authorization, Content-Type, X-Request-ID')
            self.send_header('Content-Length','0');self.end_headers()
        except Problem as e:self._send(e.status,e.as_dict())

    def do_GET(self):self._handle('GET')
    def do_POST(self):self._handle('POST')
    def do_DELETE(self):self._handle('DELETE')

    def _handle(self,method):
        try:
            self._boundary()
            url=urlsplit(self.path)
            require(not url.scheme and not url.netloc,'invalid_path','Use an origin-relative API path.',400)
            path=url.path;query=parse_qs(url.query,keep_blank_values=True)
            if method=='GET' and path=='/ready':
                require(not query,'invalid_query','This route takes no query parameters.',400)
                result=self.server.service.readiness()
                return self._send(200 if result['status']=='ready' else 503,result)
            if method=='GET' and path=='/health':
                return self._send(200,{'status':'ok','version':'0.2.0','adapter':self.server.service.extractor.name,
                    'live_ocr':self.server.service.extractor.name!='fixture','storage':'sqlite','deployment':'loopback prototype' if ipaddress.ip_address(self.server.server_address[0]).is_loopback else 'LAN prototype'})
            if method=='POST' and path=='/api/sessions':
                require(not query,'invalid_query','This route takes no query parameters.',400)
                return self._send(201,self.server.service.create_session(self._body()))
            match=re.fullmatch(r'/api/sessions/([A-Za-z0-9_-]{8,80})(?:/(.*))?',path)
            require(match is not None,'not_found','Unknown API route.',404)
            sid,tail=match.groups();service=self.server.service
            if method=='POST' and tail=='join':
                require(not query,'invalid_query','This route takes no query parameters.',400)
                return self._send(200,service.join(sid,self._body()))
            token=self._token()
            if method=='POST' and tail in ('wakeword/start','wakeword/batch','wakeword/stop'):
                require(not query,'invalid_query','This route takes no query parameters.',400)
                return self._send(200,service.wakeword(sid,token,tail.split('/')[1],self._body(16000)))
            if method=='GET' and tail=='diagnostics':
                require(not query,'invalid_query','This route takes no query parameters.',400)
                return self._send(200,service.diagnostics(sid,token))
            if method=='GET' and tail is None:
                require(set(query)<={'since_seq'} and all(len(v)==1 for v in query.values()),
                        'invalid_query','This route takes an optional single since_seq cursor.',400)
                if 'since_seq' in query:
                    value=query['since_seq'][0]
                    require(value.isdigit(),'invalid_cursor','since_seq must be nonnegative.',400)
                    return self._send(200,service.delta(sid,token,int(value)))
                return self._send(200,service.snapshot(sid,token))
            if method=='DELETE' and tail is None:
                require(not query,'invalid_query','This route takes no query parameters.',400)
                return self._send(200,service.delete_session(sid,token))
            if method=='POST' and tail=='commands':
                require(not query,'invalid_query','This route takes no query parameters.',400)
                body=self._body();fields(body,('operation','payload'),('control_sequence',))
                return self._send(200,service.command(sid,token,self.headers.get('X-Request-ID'),body['operation'],body['payload'],body.get('control_sequence')))
            if method=='POST' and tail=='export-snapshot':
                require(not query,'invalid_query','This route takes no query parameters.',400)
                return self._send(200,service.export_snapshot(sid,token,self._body()),filename=f'{sid}-snapshot.json')
            if method=='GET' and tail=='events':
                require(set(query)<= {'after'} and all(len(v)==1 for v in query.values()),'invalid_query','Use a single after cursor.',400)
                value=query.get('after',['0'])[0];require(value.isdigit(),'invalid_cursor','after must be nonnegative.',400)
                return self._send(200,service.events(sid,token,int(value)))
            cropped=re.fullmatch(r'sources/([A-Za-z0-9_-]{8,80})/regions/([A-Za-z0-9_-]{8,80})',tail or '')
            if method=='GET' and cropped:
                require(set(query)=={'revision'} and len(query['revision'])==1 and query['revision'][0].isdigit(),
                        'invalid_revision','Crop requests require one source revision.',400)
                mime,raw=service.crop(sid,token,cropped[1],int(query['revision'][0]),cropped[2])
                return self._send(200,raw,mime)
            match=re.fullmatch(r'(records|sources|exports)/([A-Za-z0-9_-]{8,80})(/media)?',tail or '')
            require(method=='GET' and match is not None,'not_found','Unknown API route.',404)
            kind,rid,media=match.groups()
            if kind=='sources' and media:
                require(not query,'invalid_query','This route takes no query parameters.',400)
                mime,raw=service.media(sid,token,rid);return self._send(200,raw,mime)
            if kind=='records' and media is None:
                require(set(query)<= {'revision'} and all(len(v)==1 for v in query.values()),'invalid_query','Use one revision query parameter.',400)
                rev=query.get('revision',[None])[0]
                require(rev is None or rev.isdigit(),'invalid_revision','revision must be a positive integer.',400)
                return self._send(200,service.record(sid,token,rid,int(rev) if rev is not None else None))
            if kind=='exports' and media is None:
                require(set(query)<= {'format'} and all(len(v)==1 for v in query.values()),'invalid_query','Use one format query parameter.',400)
                fmt=query.get('format',['json'])[0];require(fmt in ('json','markdown'),'invalid_format','Choose json or markdown.')
                record=service.record(sid,token,rid);require(record['kind']=='export','not_found','Export not found.',404)
                if fmt=='json':return self._send(200,record['data'],filename=f'{rid}.json')
                return self._send(200,record['data']['markdown'].encode('utf-8'),'text/markdown; charset=utf-8',f'{rid}.md')
            raise Problem(404,'not_found','Unknown API route.')
        except Problem as e:self._send(e.status,e.as_dict())
        except (TimeoutError,ConnectionResetError,BrokenPipeError):self.close_connection=True
        except Exception:self._send(500,{'error':{'code':'internal_error','message':'The operation failed; its outcome may be uncertain. Retain request identity and refresh.','details':{}}})
