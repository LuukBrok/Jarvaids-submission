import base64
from contextlib import closing
from io import BytesIO
import json
import sqlite3
import unittest
from unittest.mock import patch
from PIL import Image, PngImagePlugin
import test_membership as helpers
from genai_server.db import SCHEMA
from genai_server.service import Service
from genai_server.media import sanitise
from genai_server.validation import Problem


def image_bytes(size=(4,2),exif=False):
    image=Image.new('RGB',size,'red');output=BytesIO()
    if exif:
        metadata=Image.Exif();metadata[274]=6;metadata[270]='PRIVATE_GPS_SENTINEL'
        image.save(output,format='JPEG',exif=metadata)
    else:
        metadata=PngImagePlugin.PngInfo();metadata.add_text('Comment','PRIVATE_GPS_SENTINEL')
        image.save(output,format='PNG',pnginfo=metadata)
    return output.getvalue()


class MediaTests(unittest.TestCase):
    setUp=helpers.MembershipTests.setUp
    command=helpers.MembershipTests.command
    active=helpers.MembershipTests.active
    snap=helpers.MembershipTests.snap
    refuses=helpers.MembershipTests.refuses
    invite=helpers.MembershipTests.invite
    join=helpers.MembershipTests.join

    def upload(self,raw=None,mime='image/png'):
        return self.command('source.image',{'mime':mime,'base64':base64.b64encode(raw or image_bytes()).decode(),
            'regions':[{'id':'region_001','box':[0,0,.5,1]}]})

    def test_intake_strips_metadata_and_appended_bytes(self):
        self.active();source=self.upload(image_bytes()+b'APPENDED_PRIVATE_SENTINEL')
        mime,raw=self.service.media(self.sid,self.token,source['id'])
        self.assertEqual('image/png',mime)
        self.assertNotIn(b'PRIVATE',raw)
        with Image.open(BytesIO(raw)) as decoded:
            self.assertEqual({},decoded.info)
            self.assertEqual((4,2),decoded.size)
        with self.service.db.transaction() as c:
            rows=list(c.execute('SELECT payload FROM media'))
            self.assertEqual(1,len(rows));self.assertEqual(raw,rows[0]['payload'])

    def test_orientation_is_applied_before_crop_coordinates(self):
        original=Image.new('RGB',(20,10),'red')
        original.paste('green',(10,0,20,5));original.paste('blue',(0,5,10,10));original.paste('yellow',(10,5,20,10))
        metadata=Image.Exif();metadata[274]=6;stream=BytesIO()
        original.save(stream,format='JPEG',quality=100,subsampling=0,exif=metadata)
        self.active();source=self.upload(stream.getvalue(),'image/jpeg')
        self.assertEqual((10,20),(source['data']['width'],source['data']['height']))
        _,raw=self.service.crop(self.sid,self.token,source['id'],1,'region_001')
        with Image.open(BytesIO(raw)) as decoded:
            self.assertEqual((5,20),decoded.size)
            top=decoded.getpixel((2,5));bottom=decoded.getpixel((2,15))
            self.assertGreater(top[2],200);self.assertLess(top[0],30)
            self.assertGreater(bottom[0],200);self.assertGreater(bottom[1],200);self.assertLess(bottom[2],30)
            self.assertEqual({},decoded.info)

    def test_corrupt_and_multiframe_images_are_rejected(self):
        self.active()
        self.refuses('invalid_image',lambda:self.upload(image_bytes()[:40]))
        first=Image.new('RGB',(2,2),'red');second=Image.new('RGB',(2,2),'blue');stream=BytesIO()
        first.save(stream,format='PNG',save_all=True,append_images=[second])
        self.refuses('invalid_image',lambda:self.upload(stream.getvalue()))

    def test_unrelated_and_demoted_members_cannot_read_images_or_crops(self):
        self.active();source=self.upload();cap,_=self.invite();body,joined=self.join(cap)
        for call in (lambda:self.service.media(self.sid,body['token'],source['id']),
                     lambda:self.service.crop(self.sid,body['token'],source['id'],1,'region_001')):
            self.refuses('forbidden',call)
        self.command('participant.role',{'actor_id':joined['actor_id'],'role':'facilitator','expected_roster_revision':self.snap()['session']['roster_revision']})
        self.assertEqual('image/png',self.service.media(self.sid,body['token'],source['id'])[0])
        self.command('participant.role',{'actor_id':joined['actor_id'],'role':'viewer','expected_roster_revision':self.snap()['session']['roster_revision']})
        self.refuses('forbidden',lambda:self.service.media(self.sid,body['token'],source['id']))

    def test_crop_authority_denies_before_decoding(self):
        self.active();source=self.upload();cap,_=self.invite();body,_=self.join(cap)
        with patch('genai_server.service.crop_pixels',return_value=b'not generated') as render:
            self.refuses('forbidden',lambda:self.service.crop(self.sid,body['token'],source['id'],1,'region_001'))
            self.assertEqual(0,render.call_count,'Unauthorised callers must not trigger image decoding')

    def test_crop_revision_conflict_and_deletion_during_render(self):
        self.active();source=self.upload()
        self.command('source.regions',{'source_id':source['id'],'expected_revision':1,'regions':[{'id':'region_002','box':[0,0,1,1]}]})
        self.refuses('stale_revision',lambda:self.service.crop(self.sid,self.token,source['id'],1,'region_001'))
        def deleted(raw,box):
            self.service.delete_session(self.sid,self.token)
            return b'never return this'
        with patch('genai_server.service.crop_pixels',deleted):
            self.refuses('unauthorized',lambda:self.service.crop(self.sid,self.token,source['id'],2,'region_002'))

    def test_region_history_and_duplicates_store_one_media_payload(self):
        self.active();source=self.upload();self.upload()
        for revision in range(1,9):
            self.command('source.regions',{'source_id':source['id'],'expected_revision':revision,
                'regions':[{'id':'region_001','box':[0,0,.5,1]}]})
        with self.service.db.transaction() as c:
            self.assertEqual(1,c.execute('SELECT count(*) FROM media').fetchone()[0])
            for row in c.execute('SELECT data FROM versions'):
                self.assertNotIn('base64',json.loads(row['data']))
        self.service.delete_session(self.sid,self.token)
        with self.service.db.transaction() as c:self.assertEqual(0,c.execute('SELECT count(*) FROM media').fetchone()[0])

    def test_legacy_originals_are_removed_from_history_and_retry_results(self):
        legacy=self.service.db.path.parent/'legacy.sqlite3'
        raw=image_bytes()+b'APPENDED_PRIVATE_SENTINEL';encoded=base64.b64encode(raw).decode()
        data={'type':'image','mime':'image/png','base64':encoded,'author_id':'actor_001','regions':[]}
        with closing(sqlite3.connect(legacy)) as c,c:
            c.executescript(SCHEMA)
            c.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?,?)',('session_001','Legacy','draft',1,0,0,999999,99999,None,None))
            c.execute('INSERT INTO records VALUES(?,?,?,?,?)',('source_001','session_001','source',1,json.dumps(data)))
            c.execute('INSERT INTO versions VALUES(?,?,?,?)',('session_001','source_001',1,json.dumps(data)))
            c.execute('INSERT INTO requests VALUES(?,?,?,?,?)',('session_001','actor_001','request_001','hash',json.dumps({'result':data})))
        migrated=Service(legacy,clock=lambda:1000)
        with migrated.db.transaction() as c:
            self.assertEqual(6,c.execute('PRAGMA user_version').fetchone()[0])
            self.assertEqual(1,c.execute('SELECT count(*) FROM media').fetchone()[0])
            self.assertNotIn(encoded,'\n'.join(c.iterdump()))
            self.assertNotIn(b'PRIVATE',c.execute('SELECT payload FROM media').fetchone()[0])
        Service(legacy,clock=lambda:1000)

    def test_unsupported_schema_is_not_silently_downgraded(self):
        legacy=self.service.db.path.parent/'future.sqlite3'
        with closing(sqlite3.connect(legacy)) as c,c:c.execute('PRAGMA user_version=99')
        with self.assertRaisesRegex(RuntimeError,'Unsupported'):Service(legacy)
        with closing(sqlite3.connect(legacy)) as c:self.assertEqual(99,c.execute('PRAGMA user_version').fetchone()[0])

    def legacy(self,encoded,mime='image/png'):
        path=self.service.db.path.parent/'legacy.sqlite3'
        data={'type':'image','mime':mime,'base64':encoded,'author_id':'actor_001','regions':[]}
        with closing(sqlite3.connect(path)) as c,c:
            c.executescript(SCHEMA)
            c.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?,?)',('session_001','Legacy','draft',1,0,0,999999,99999,None,None))
            c.execute('INSERT INTO records VALUES(?,?,?,?,?)',('source_001','session_001','source',1,json.dumps(data)))
            c.execute('INSERT INTO versions VALUES(?,?,?,?)',('session_001','source_001',1,json.dumps(data)))
        return path

    def test_invalid_legacy_bytes_are_unavailable_and_not_retained(self):
        path=self.legacy('invalid@@base64')
        migrated=Service(path,clock=lambda:1000)
        with migrated.db.transaction() as c:
            for table in ('records','versions'):
                data=json.loads(c.execute(f'SELECT data FROM {table}').fetchone()[0])
                self.assertTrue(data['media_unavailable']);self.assertNotIn('base64',data)
            self.assertEqual(0,c.execute('SELECT count(*) FROM media').fetchone()[0])

    def test_interrupted_media_migration_rolls_back_and_restarts(self):
        encoded=base64.b64encode(image_bytes()).decode();path=self.legacy(encoded)
        with patch('genai_server.db.sanitise',side_effect=RuntimeError('synthetic interruption')):
            with self.assertRaisesRegex(RuntimeError,'interruption'):Service(path)
        with closing(sqlite3.connect(path)) as c:
            self.assertEqual(2,c.execute('PRAGMA user_version').fetchone()[0])
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='media'").fetchone())
            self.assertEqual(encoded,json.loads(c.execute('SELECT data FROM records').fetchone()[0])['base64'])
        recovered=Service(path,clock=lambda:1000)
        with recovered.db.transaction() as c:
            self.assertEqual(6,c.execute('PRAGMA user_version').fetchone()[0])
            self.assertEqual(1,c.execute('SELECT count(*) FROM media').fetchone()[0])

    def test_legacy_regions_follow_orientation_transform(self):
        path=self.legacy(base64.b64encode(image_bytes(exif=True)).decode(),'image/jpeg')
        with closing(sqlite3.connect(path)) as c,c:
            for table in ('records','versions'):
                data=json.loads(c.execute(f'SELECT data FROM {table}').fetchone()[0])
                data['regions']=[{'id':'region_001','box':[0,0,.5,1]}]
                c.execute(f'UPDATE {table} SET data=?',(json.dumps(data),))
        migrated=Service(path,clock=lambda:1000)
        with migrated.db.transaction() as c:
            for table in ('records','versions'):
                data=json.loads(c.execute(f'SELECT data FROM {table}').fetchone()[0])
                self.assertEqual([0,0,1,.5],data['regions'][0]['box'])
                self.assertEqual((2,4),(data['width'],data['height']))
