"""Named media mutations run in disposable copies; errors never count as kills."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mutation_runner import check_one_target

MUTANTS = [
    ('compressed-input-cap', 'test_compressed_input_has_a_fixed_four_mib_limit',
     "require(len(raw)<=4*1024*1024,", "require(True,"),
    ('encoded-output-cap', 'test_encoded_output_has_a_fixed_four_mib_limit',
     "require(self.tell()+len(value)<=MAX_OUTPUT,", "require(True,"),
    ('pixel-cap', 'test_pixel_limit_rejects_valid_highly_compressed_image',
     'and width*height<=MAX_PIXELS,', ','),
    ('dimension-cap', 'test_dimension_limit_is_independent_of_pixel_count',
     '0<width<=12000 and 0<height<=12000', '0<width and 0<height'),
    ('multiframe-rejection', 'test_animation_is_not_silently_reduced_to_one_frame',
     "require(getattr(probe,'n_frames',1)==1,", "require(True,"),
    ('mime-decoder', 'test_mime_must_match_the_actual_decoder',
     "require(probe.format=={'image/png':'PNG','image/jpeg':'JPEG'}[mime],", "require(True,"),
    ('orientation', 'test_exif_rotation_changes_pixels_in_the_correct_direction',
     'oriented=ImageOps.exif_transpose(decoded)', 'oriented=decoded'),
    ('metadata-isolation', 'test_clean_pixels_do_not_carry_exif_or_appended_sentinels',
     "clean.save(output,format='PNG')", "clean.save(output,format='PNG',exif=decoded.getexif())"),
    ('full-decode', 'test_valid_crc_does_not_substitute_for_pixel_decoding',
     'decoded.load()', 'return raw,mime,decoded.width,decoded.height'),
]


def main():
    return check_one_target('media.py', MUTANTS, 'test_media_guards.py', 60, 'media')


if __name__ == '__main__':
    raise SystemExit(main())
