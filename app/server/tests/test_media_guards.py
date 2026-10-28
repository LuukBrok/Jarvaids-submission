"""Valid synthetic images and fixed limits make decoder guards observable."""
from io import BytesIO
import struct
import unittest
import zlib

from PIL import Image

from genai_server.media import BoundedOutput, sanitise
from genai_server.validation import Problem


def png(size=(2, 2), exif=None):
    output = BytesIO()
    with Image.new('RGB', size, 'red') as image:
        image.save(output, format='PNG', **({'exif':exif} if exif is not None else {}))
    return output.getvalue()


class MediaGuardTests(unittest.TestCase):
    def refuses(self, code, callback):
        with self.assertRaises(Problem) as caught:
            callback()
        self.assertEqual(code, caught.exception.code)

    def test_compressed_input_has_a_fixed_four_mib_limit(self):
        raw = png()
        raw += b'x' * (4 * 1024 * 1024 + 1 - len(raw))
        self.refuses('image_too_large', lambda:sanitise(raw, 'image/png'))

    def test_encoded_output_has_a_fixed_four_mib_limit(self):
        with BoundedOutput() as output:
            self.refuses('image_too_large', lambda:output.write(b'x' * (4 * 1024 * 1024 + 1)))
            self.assertEqual(0, len(output.getvalue()))

    def test_pixel_limit_rejects_valid_highly_compressed_image(self):
        self.refuses('image_too_large', lambda:sanitise(png((5001, 4000)), 'image/png'))

    def test_dimension_limit_is_independent_of_pixel_count(self):
        self.refuses('image_too_large', lambda:sanitise(png((12001, 1)), 'image/png'))

    def test_animation_is_not_silently_reduced_to_one_frame(self):
        output = BytesIO()
        with Image.new('RGB', (2, 2), 'red') as first, Image.new('RGB', (2, 2), 'blue') as second:
            first.save(output, format='PNG', save_all=True, append_images=[second])
        self.refuses('invalid_image', lambda:sanitise(output.getvalue(), 'image/png'))

    def test_mime_must_match_the_actual_decoder(self):
        self.refuses('invalid_image', lambda:sanitise(png(), 'image/jpeg'))

    def test_exif_rotation_changes_pixels_in_the_correct_direction(self):
        original = Image.new('RGB', (2, 3))
        colours = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (255,0,255), (0,255,255)]
        original.putdata(colours)
        exif = Image.Exif()
        exif[274] = 6
        stream = BytesIO()
        original.save(stream, format='PNG', exif=exif)
        clean, _, width, height = sanitise(stream.getvalue(), 'image/png')
        self.assertEqual((3, 2), (width, height))
        with Image.open(BytesIO(clean)) as result:
            for y in range(3):
                for x in range(2):
                    self.assertEqual(original.getpixel((x,y)), result.getpixel((2-y,x)))
        original.close()

    def test_clean_pixels_do_not_carry_exif_or_appended_sentinels(self):
        exif = Image.Exif()
        exif[270] = 'PRIVATE_METADATA_SENTINEL'
        clean, _, _, _ = sanitise(png(exif=exif) + b'PRIVATE_APPENDED_SENTINEL', 'image/png')
        self.assertNotIn(b'PRIVATE_', clean)
        with Image.open(BytesIO(clean)) as image:
            self.assertEqual({}, image.info)
            self.assertEqual(0, len(image.getexif()))

    def test_valid_crc_does_not_substitute_for_pixel_decoding(self):
        def chunk(kind, payload):
            return struct.pack('>I',len(payload)) + kind + payload + struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
        raw = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR',struct.pack('>IIBBBBB',2,2,8,2,0,0,0))
               + chunk(b'IDAT',b'not a deflate stream') + chunk(b'IEND',b''))
        self.refuses('invalid_image', lambda:sanitise(raw, 'image/png'))
