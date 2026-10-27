import contextlib
import io
import tempfile
import unittest
from pathlib import Path
import organize_anime as o

class OrganizerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent); self.addCleanup(self.tmp.cleanup)
  self.base=Path(self.tmp.name); self.src=self.base/'source'; self.src.mkdir(); self.dst=self.src; self.movies=self.base/'Movies'; self.movies.mkdir(); (self.src/'Test').mkdir()
 def file(self,name,data=b'video'):
  if '/' not in name: name='Test/'+name
  p=self.src/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(data); return p
 def plan(self,rules=None): return o.make_plan(self.src,self.dst,rules,movies_root=self.movies)
 def run_quiet(self,fn,*args):
  with contextlib.redirect_stdout(io.StringIO()): return fn(*args)
 def test_release_patterns(self):
  for name,expected in [('[SubsPlease] Test S3 - 01v2 (1080p) [ABC].mkv',('Test',3,1)),('[Erai] Test 2nd Season - 02 [1080p].mkv',('Test',2,2)),('[Group] Test IV - 03 [720p].mkv',('Test',4,3)),('Test.Show.S01E04.Title.mkv',('Test Show',1,4)),('Test.S01E04.1080p.WEB.mkv',('Test',1,4)),('[SubsWhen][Isekai Ojisan][08][1080p].mkv',('Isekai Ojisan',1,8))]:
   self.assertEqual(o.parse_name(self.src/name,self.src)[:3],expected)
 def test_range(self):
  self.assertEqual(o.parse_name(self.src/'Test S01E01-E02.mkv',self.src)[2:4],(1,2))
  self.assertEqual(o.parse_name(self.src/'[Fansub] Test - 01-02 [1080p].mkv',self.src)[2:4],(1,2))
 def test_ambiguous(self):
  for name in ['Test - 12.5.mkv','Test OVA - 01.mkv','Test - 00.mkv','Test - 51.mkv','Test 2 - 01.mkv','Test - Arc-hen - 01.mkv','Test movie.mkv']:
   with self.subTest(name=name),self.assertRaises(ValueError): o.parse_name(self.src/name,self.src)
 def test_companions_and_metadata(self):
  self.file('Test/[G] Test - 01 [1080p].mkv')
  self.file('Test/[G] Test - 01 [1080p].pt-BR.ass',b'sub')
  self.file('Test/[G] Test - 01 [1080p].nfo',b'<episodedetails/>')
  self.file('Test/[G] Test - 01 [1080p]-thumb.jpg',b'picture')
  self.file('Test/[G] Test - 01 [1080p].trickplay/320/0.jpg',b'trickplay')
  p=self.plan(); self.assertEqual(len(p['entries']),3)
  self.assertEqual(p['inventory']['counts']['jellyfin_nfo'],1)
  self.assertEqual(p['inventory']['counts']['jellyfin_trickplay'],1)
  self.assertFalse((self.src/'Shows').exists()); self.assertFalse((self.src/'Movies').exists()); self.assertFalse((self.src/'Test'/'Season 01').exists())
 def test_collision(self):
  self.file('[A] Test - 01.mkv'); self.file('[B] Test - 01.mkv')
  p=self.plan(); self.assertFalse(p['blocked']); self.assertNotEqual(p['entries'][0]['destination'],p['entries'][1]['destination'])
 def test_all_modes_and_undo(self):
  original=self.file('Test - 01.mkv')
  for mode in ['copy','move']:
   with self.subTest(mode=mode):
    p=self.plan(); journal=self.base/(mode+'.jsonl')
    self.run_quiet(o.apply,p,journal,mode)
    dest=Path(p['entries'][0]['destination'])
    self.assertEqual(dest.read_bytes(),b'video')
    self.assertEqual(original.exists(),mode!='move')
    if mode=='hardlink': self.assertTrue(original.samefile(dest))
    self.run_quiet(o.undo,journal); self.run_quiet(o.undo,journal)
    self.assertTrue(original.exists()); self.assertFalse(dest.exists())
 def test_hardlink(self):
  original=self.file('Test - 01.mkv'); p=self.plan(); journal=self.base/'hardlink.jsonl'
  try: self.run_quiet(o.apply,p,journal,'hardlink')
  except PermissionError as exc: self.skipTest(f'Environment denied hardlink creation: {exc.errno}')
  dest=Path(p['entries'][0]['destination'])
  self.assertTrue(original.samefile(dest))
  self.run_quiet(o.undo,journal)
  self.assertTrue(original.exists()); self.assertFalse(dest.exists())
 def test_thumbnails_do_not_cross_episodes(self):
  for ep in [1,2]:
   self.file(f'Test - {ep:02}.mkv'); self.file(f'Test - {ep:02}-thumb.jpg')
  p=self.plan(); self.assertEqual(len(p['entries']),4); self.assertFalse(p['blocked'])
 def test_existing_destination(self):
  self.file('Test - 01.mkv'); p=self.plan(); d=Path(p['entries'][0]['destination']); d.parent.mkdir(parents=True,exist_ok=True); d.write_bytes(b'keep')
  with self.assertRaises(ValueError): o.apply(p,self.base/'j.jsonl')
  self.assertEqual(d.read_bytes(),b'keep')
 def test_source_changed(self):
  f=self.file('Test - 01.mkv'); p=self.plan(); f.write_bytes(b'changed')
  with self.assertRaises(ValueError): o.apply(p,self.base/'j.jsonl')
 def test_target_changed_blocks_undo(self):
  self.file('Test - 01.mkv'); p=self.plan(); j=self.base/'j.jsonl'
  self.run_quiet(o.apply,p,j,'copy'); d=Path(p['entries'][0]['destination']); d.write_bytes(b'changed')
  with self.assertRaises(ValueError): o.undo(j)
 def test_file_rule_special(self):
  self.file('Test OVA.mkv')
  p=self.plan({'files':{'Test/Test OVA.mkv':{'series':'Test','season':0,'episode':3,'provider_id':'tmdbid-123'}}})
  self.assertIn('Test [tmdbid-123]',Path(p['entries'][0]['destination']).name); self.assertIn('S00E03',p['entries'][0]['destination'])
 def test_folder_rule_absolute(self):
  self.file('Re Zero/[G] Re Zero - 51.mkv')
  p=self.plan({'folders':{'Re Zero':{'series':'Re Zero','season':3,'episode_offset':-50}}})
  self.assertIn('S03E01',p['entries'][0]['destination'])
 def test_movie_rule(self):
  self.file('Test movie.mkv')
  p=self.plan({'files':{'Test/Test movie.mkv':{'type':'movie','title':'Test Movie','year':2024,'provider_id':'tmdbid-123'}}})
  d=Path(p['entries'][0]['destination'])
  self.assertEqual(d.parent,self.movies); self.assertIn('Test Movie (2024)',d.stem)
 def test_inplace_move_and_undo_without_reading_contents(self):
  from unittest.mock import patch
  original=self.file('Test - 01.mkv')
  p=o.make_plan(self.src,self.src,movies_root=self.movies); j=self.base/'inplace.jsonl'
  with patch.object(o, 'exclusive_copy', side_effect=AssertionError('Move must not copy')):
   self.run_quiet(o.apply,p,j,'move')
   dest=Path(p['entries'][0]['destination'])
   self.assertTrue(dest.exists()); self.assertFalse(original.exists())
   self.assertEqual(o.make_plan(self.src,self.src,movies_root=self.movies)['entries'],[])
   self.run_quiet(o.undo,j)
  self.assertTrue(original.exists()); self.assertFalse(dest.exists())
 def test_no_new_anime_directories(self):
  self.file('Different Folder/[G] Different Title S2 - 01.mkv')
  before={p for p in self.src.rglob('*') if p.is_dir()}
  plan=self.plan(); self.run_quiet(o.apply,plan,self.base/'flat.jsonl','move')
  after={p for p in self.src.rglob('*') if p.is_dir()}
  self.assertEqual(before,after)
  for e in plan['entries']: self.assertEqual(Path(e['destination']).parent,Path(e['source']).parent)
 def test_loose_episode_needs_existing_folder(self):
  p=self.src/'[G] Unknown Series - 01.mkv'; p.write_bytes(b'video')
  result=self.plan(); self.assertEqual(result['entries'],[]); self.assertEqual(len(result['review']),1)
 def test_detected_movie_goes_to_existing_movies(self):
  self.file('[G] Overlord - Sei Oukoku-hen - Movie [1080p].mkv')
  plan=self.plan(); self.assertEqual(len(plan['entries']),1)
  self.assertEqual(Path(plan['entries'][0]['destination']).parent,self.movies)
 def test_nested_anime_directory_rejected(self):
  self.file('Test - 01.mkv'); plan=self.plan()
  plan['entries'][0]['destination']=str(self.src/'Test'/'Season 01'/'Test S01E01.mkv')
  with self.assertRaises(ValueError): o.validate_plan(plan)
 def test_old_layout_rejected(self):
  with self.assertRaises(ValueError): o.validate_plan({'version':1,'blocked':False})
 def test_cleanup_preserves_video_and_subtitles(self):
  import clean_images_nfo as c
  from unittest.mock import patch
  video=self.file('Test - 01.mkv'); subtitle=self.file('Test - 01.srt')
  image=self.file('poster.JPG'); nfo=self.file('tvshow.nfo')
  with patch.object(c,'BASE',self.base):
   self.run_quiet(c.cleanup,[self.src,self.movies],True)
  self.assertTrue(video.exists()); self.assertTrue(subtitle.exists())
  self.assertFalse(image.exists()); self.assertFalse(nfo.exists())
 def test_non_nested_roots(self):
  with self.assertRaises(ValueError): o.make_plan(self.src,self.src/'output')
 def test_escape_plan(self):
  self.file('Test - 01.mkv'); p=self.plan(); p['entries'][0]['destination']=str(self.base/'escape.mkv')
  with self.assertRaises(ValueError): o.apply(p,self.base/'j.jsonl')
 def test_unicode(self):
  self.file('[G] 転生剣 - 01.mkv')
  self.assertIn('転生剣',self.plan()['entries'][0]['destination'])

if __name__=='__main__': unittest.main()
