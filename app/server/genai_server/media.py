"""Offline pixel decoding and clean re-encoding; no original metadata is retained."""
from io import BytesIO
import math
from PIL import Image, ImageOps
from .validation import Problem, require

MAX_OUTPUT=4*1024*1024
MAX_PIXELS=20_000_000


class BoundedOutput(BytesIO):
    def write(self,value):
        require(self.tell()+len(value)<=MAX_OUTPUT,'image_too_large','Sanitised image exceeds 4 MiB.',413)
        return super().write(value)


def sanitise(raw,mime):
    require(mime in ('image/png','image/jpeg'),'invalid_image','Only PNG and JPEG are supported.')
    require(len(raw)<=4*1024*1024,'image_too_large','Image exceeds 4 MiB.',413)
    try:
        with Image.open(BytesIO(raw),formats=['PNG','JPEG']) as probe:
            require(probe.format=={'image/png':'PNG','image/jpeg':'JPEG'}[mime],'invalid_image','Image MIME does not match its pixels.')
            width,height=probe.size
            require(0<width<=12000 and 0<height<=12000 and width*height<=MAX_PIXELS,'image_too_large','Image dimensions exceed the pixel limit.',413)
            require(getattr(probe,'n_frames',1)==1,'invalid_image','Multiframe images are not supported.')
            probe.verify()
        with Image.open(BytesIO(raw),formats=['PNG','JPEG']) as decoded:
            decoded.load()
            oriented=ImageOps.exif_transpose(decoded)
            # Flatten alpha onto white and discard colour profiles. RGB values
            # are interpreted as sRGB; no colour-fidelity claim is made for ICC input.
            rgba=oriented.convert('RGBA')
            clean=Image.new('RGB',rgba.size,'white')
            clean.paste(rgba,mask=rgba.getchannel('A'))
            output=BoundedOutput();clean.save(output,format='PNG')
            return output.getvalue(),'image/png',clean.width,clean.height
    except Problem:raise
    except (OSError,ValueError,SyntaxError,Image.DecompressionBombError):
        raise Problem(422,'invalid_image','Image could not be fully decoded.')


def crop(raw,box):
    with Image.open(BytesIO(raw)) as original:
        x,y,w,h=box
        bounds=(math.floor(x*original.width),math.floor(y*original.height),
                min(original.width,math.ceil((x+w)*original.width)),
                min(original.height,math.ceil((y+h)*original.height)))
        pixels=original.crop(bounds)
        output=BoundedOutput();pixels.save(output,format='PNG')
        return output.getvalue()
