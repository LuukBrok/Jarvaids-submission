"""Small strict boundary validators shared by commands and adapters."""
import base64
import binascii
import math
import re
import struct


class Problem(Exception):
    def __init__(self, status, code, message, **details):
        self.status, self.code, self.message, self.details = status, code, message, details
        super().__init__(message)

    def as_dict(self):
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


def require(condition, code, message, status=422, **details):
    if not condition:
        raise Problem(status, code, message, **details)


def fields(body, required=(), optional=()):
    require(type(body) is dict, "invalid_object", "Expected a JSON object.")
    require(set(required) <= body.keys(), "missing_fields", "Required fields are missing.", fields=sorted(set(required)-body.keys()))
    require(not body.keys()-set(required)-set(optional), "unknown_fields", "Unknown fields are not accepted.", fields=sorted(body.keys()-set(required)-set(optional)))


def text(value, name, limit=10000, empty=False):
    require(type(value) is str and (empty or bool(value.strip())) and len(value) <= limit,
            "invalid_text", f"{name} must be {'possibly empty ' if empty else 'non-empty '}text up to {limit} characters.")
    require(not any(ord(c)<32 and c not in '\n\r\t' for c in value), "invalid_text", f"{name} contains control characters.")
    # Unpaired surrogates reach here from callers that do not come through the
    # HTTP boundary, and they only fail later, at encode, as a 500.
    if not value.isascii():
        try:value.encode('utf-8')
        except UnicodeEncodeError:
            raise Problem(422,"invalid_text",f"{name} contains unpaired surrogates.")
    return value


def ident(value):
    require(type(value) is str and re.fullmatch(r"[A-Za-z0-9_-]{8,80}", value) is not None,
            "invalid_id", "IDs must contain 8–80 letters, digits, underscores or hyphens.")
    return value


def integer(value, name, low=1, high=1000000000):
    require(type(value) is int and low <= value <= high, "invalid_integer", f"{name} must be an integer from {low} to {high}.")
    return value


def credential(value):
    require(type(value) is str and re.fullmatch(r"[A-Za-z0-9_-]{32,128}",value) is not None,
            "invalid_credential", "Use a client-generated cryptographically random URL-safe token of 32–128 characters.")
    return value


def regions(value):
    require(type(value) is list and 1 <= len(value) <= 60, "invalid_regions", "Supply 1–60 regions.")
    seen=set()
    for region in value:
        fields(region, ("id", "box"))
        ident(region['id'])
        require(region['id'] not in seen, "duplicate_region", "Region IDs must be unique.")
        seen.add(region['id'])
        b=region['box']
        require(type(b) is list and len(b)==4 and all(type(v) in (int,float) and math.isfinite(v) for v in b),
                "invalid_box", "A box is normalized [x,y,width,height].")
        x,y,w,h=b
        require(x>=0 and y>=0 and w>0 and h>0 and x+w<=1.0000001 and y+h<=1.0000001,
                "invalid_box", "Region boxes must fit inside the normalized image.")
    return value


def image_payload(encoded, mime):
    require(mime in ('image/png','image/jpeg'), "unsupported_media", "Only PNG and JPEG are accepted.")
    require(type(encoded) is str and len(encoded)<=5600000, "image_too_large", "Image exceeds the 4 MiB input limit.",413)
    try:
        raw=base64.b64decode(encoded,validate=True)
    except (ValueError,binascii.Error):
        raise Problem(422,"invalid_base64","Image must be valid base64.")
    require(0<len(raw)<=4*1024*1024,"image_too_large","Image exceeds the 4 MiB input limit.",413)
    width=height=0
    if mime=='image/png':
        require(raw.startswith(b'\x89PNG\r\n\x1a\n') and len(raw)>=33 and raw[12:16]==b'IHDR',"invalid_image","Invalid PNG header.")
        width,height=struct.unpack('>II',raw[16:24])
    else:
        require(raw.startswith(b'\xff\xd8') and raw.endswith(b'\xff\xd9'),"invalid_image","Invalid JPEG framing.")
        p=2
        while p+3<len(raw):
            require(raw[p]==255,"invalid_image","Invalid JPEG marker.")
            while p<len(raw) and raw[p]==255:p+=1
            require(p<len(raw),"invalid_image","Truncated JPEG marker.")
            marker=raw[p];p+=1
            if marker in (0xD8,0xD9) or 0xD0<=marker<=0xD7:continue
            require(p+2<=len(raw),"invalid_image","Truncated JPEG segment.")
            size=int.from_bytes(raw[p:p+2],'big')
            require(size>=2 and p+size<=len(raw),"invalid_image","Invalid JPEG segment length.")
            if marker in (0xC0,0xC1,0xC2):
                require(size>=8,"invalid_image","Truncated JPEG frame.")
                height,width=struct.unpack('>HH',raw[p+3:p+7]);break
            if marker==0xDA:break
            p+=size
    require(width>0 and height>0 and width*height<=20000000 and max(width,height)<=12000,
            "invalid_dimensions","Image dimensions must be available and no larger than 20 MP / 12000px.")
    # Header checks bound metadata; they are not full pixel decoding or malware scanning.
    return raw,width,height


# S4 in pipelines.md: 0.6-12s chunk, 16 kHz mono 16-bit PCM. 12s * 16000 * 2
# bytes = 384000 bytes; the base64 cap allows a little framing overhead.
def audio_payload(encoded, mime):
    require(mime=='audio/pcm16', "unsupported_media", "Only 16-bit PCM audio is accepted.")
    require(type(encoded) is str and len(encoded)<=520000, "audio_too_large", "Chunk exceeds the 12 second capture limit.",413)
    try:
        raw=base64.b64decode(encoded,validate=True)
    except (ValueError,binascii.Error):
        raise Problem(422,"invalid_base64","Audio chunk must be valid base64.")
    require(len(raw)%2==0, "invalid_audio", "PCM16 audio must have an even byte count.")
    sample_rate=16000
    duration_ms=round(len(raw)/2/sample_rate*1000)
    require(600<=duration_ms<=12000, "invalid_duration", "A chunk must be 0.6 to 12 seconds, per the endpointing budget in pipelines.md S4.")
    return raw,sample_rate,duration_ms
