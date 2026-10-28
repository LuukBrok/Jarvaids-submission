"""Manifest failures are tested without installing the optional inference engine."""
import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch, Mock

from genai_server.validation import Problem
from genai_server.wakeword import LocalDetector, BATCH_BYTES


class ModelTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='jv-model-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest = {'phrase':'Hey Jarvaids', 'pronunciation':'Hey Jar-vaydz',
                         'engine_version':'0.6.0', 'assets':{}}
        for name in ('keyword', 'melspectrogram', 'embedding'):
            data = name.encode()
            (self.root / (name + '.onnx')).write_bytes(data)
            self.manifest['assets'][name] = {'file':name + '.onnx',
                'sha256':hashlib.sha256(data).hexdigest(), 'licence':'test-only', 'source':'synthetic fixture'}

    def load(self):
        path = self.root / 'manifest.json'
        path.write_text(json.dumps(self.manifest))
        with patch.dict('sys.modules', {'numpy':types.SimpleNamespace()}), \
             patch('importlib.metadata.version', return_value='0.6.0'), \
             patch('genai_server.wakeword.create_engine', return_value=Mock()), \
             patch.object(LocalDetector, 'predict', return_value=0):
            return LocalDetector(path)

    def refused(self):
        try:
            self.load()
            return False
        except Problem as error:
            return error.code == 'wakeword_unavailable'

    def test_valid_manifest_has_explicit_local_assets(self):
        detector = self.load()
        self.assertEqual(detector.key, 'keyword')
        detector.model.reset.assert_called_once()

    def test_corrupt_asset_is_unavailable(self):
        (self.root / 'keyword.onnx').write_bytes(b'corrupt')
        self.assertTrue(self.refused())

    def test_other_phrase_is_never_a_fallback(self):
        self.manifest['phrase'] = 'Hey Jarvis'
        self.assertTrue(self.refused())

    def test_provenance_is_required(self):
        self.manifest['assets']['keyword']['licence'] = ''
        self.assertTrue(self.refused())

    def test_paths_cannot_escape_asset_directory(self):
        # The escaped file exists and has the right digest: only the path guard refuses it.
        outside = self.root / 'outside.onnx'
        outside.write_bytes(b'keyword')
        self.root = self.root / 'models'
        self.root.mkdir()
        for name in self.manifest['assets']:
            (self.root / (name + '.onnx')).write_bytes(name.encode())
        self.manifest['assets']['keyword']['file'] = '../outside.onnx'
        self.assertTrue(self.refused())

    def test_onnx_load_error_is_unavailable(self):
        with patch.object(LocalDetector, 'predict', side_effect=ValueError('broken tensor')):
            # load() patches predict itself, so exercise the real constructor here.
            path = self.root / 'manifest.json'
            path.write_text(json.dumps(self.manifest))
            with patch.dict('sys.modules', {'numpy':types.SimpleNamespace()}), \
                 patch('importlib.metadata.version', return_value='0.6.0'), \
                 patch('genai_server.wakeword.create_engine', side_effect=ValueError('private path')):
                with self.assertRaises(Problem) as result:
                    LocalDetector(path)
                self.assertEqual(result.exception.code, 'wakeword_unavailable')
                self.assertNotIn('private', str(result.exception))

    def test_four_80_ms_frames_preserve_order(self):
        class Samples(list):
            def astype(self, *_args, **_kwargs): return self
        detector = LocalDetector.__new__(LocalDetector)
        detector.np = types.SimpleNamespace(int16='i2', frombuffer=lambda raw, dtype:Samples(range(5120)))
        detector.key = 'keyword'
        frames = []
        detector.model = types.SimpleNamespace(predict=lambda frame:(frames.append(frame) or {'keyword':len(frames)/10}))
        self.assertEqual(detector.predict(bytes(BATCH_BYTES)), .4)
        self.assertEqual([len(frame) for frame in frames], [1280]*4)
        self.assertEqual([frame[0] for frame in frames], [0,1280,2560,3840])
