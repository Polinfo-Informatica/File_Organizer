"""Behavior tests for the central controller and read-only audit."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import audit_library
import clean_empty_folders
import clean_duplicate_videos
import clean_images_nfo
import run_local


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.anime = self.base / 'Anime'; self.anime.mkdir()
        self.movies = self.base / 'Movies'; self.movies.mkdir()
        self.settings = {'source': str(self.anime), 'movies': str(self.movies), 'jellyfin_server': str(self.base/'missing-server')}
        (self.base/'local_settings.json').write_text(json.dumps(self.settings),encoding='utf-8')

    def test_empty_preview_models_parent_without_removing_files(self):
        (self.anime/'empty'/'nested').mkdir(parents=True)
        (self.anime/'keep').mkdir(); (self.anime/'keep'/'video.mkv').write_bytes(b'x')
        result = clean_empty_folders.remove_empty([self.anime], apply=False)
        self.assertEqual(len(result['candidates']),2)
        self.assertTrue((self.anime/'empty'/'nested').is_dir())
        result = clean_empty_folders.remove_empty([self.anime], apply=True)
        self.assertEqual(len(result['removed']),2)
        self.assertTrue((self.anime/'keep'/'video.mkv').exists())
        self.assertTrue(self.anime.exists())

    def test_audit_reports_nested_duplicates_and_companions_without_mutation(self):
        folder = self.anime/'Shows'/'Series';folder.mkdir(parents=True)
        for n in ['Series - S01E01 - 720p.mkv','Series - S01E01 - 1080p.mkv','poster.jpg','file.mka']:
            (folder/n).write_bytes(b'test')
        before = {str(p):p.stat().st_size for p in folder.iterdir()}
        result = audit_library.audit(self.settings)
        self.assertEqual(result['anime']['videos'],2)
        self.assertEqual(len(result['anime']['nested_videos']),2)
        self.assertEqual(len(result['anime']['duplicate_episode_groups']),1)
        self.assertEqual(len(result['anime']['images_nfo']),1)
        self.assertEqual({str(p):p.stat().st_size for p in folder.iterdir()},before)

    def test_controller_cli_defaults_to_preview_for_deletions(self):
        poster=self.anime/'poster.jpg';poster.write_bytes(b'image')
        old=Path.cwd();self.addCleanup(lambda: __import__('os').chdir(old))
        with patch.object(run_local,'BASE',self.base),patch.object(clean_images_nfo,'BASE',self.base),contextlib.redirect_stdout(io.StringIO()):
            run_local.menu(['--action','images'])
        self.assertTrue(poster.exists())
        with patch.object(run_local,'BASE',self.base),patch.object(clean_images_nfo,'BASE',self.base),contextlib.redirect_stdout(io.StringIO()):
            run_local.menu(['--action','images','--apply'])
        self.assertFalse(poster.exists())

    def test_duplicate_preference_and_changed_keeper_protection(self):
        folder=self.anime/'Series';folder.mkdir()
        low=folder/'Series - S01E01 - 720p [aaaaaaaaaa].mkv'
        other=folder/'Series - S01E01 - 1080p [bbbbbbbbbb].mkv'
        erai=folder/'Series - S01E01 - 1080p [cccccccccc].mkv'
        for p in (low,other,erai):p.write_bytes(b'video')
        result=clean_duplicate_videos.plan_cleanup([self.anime],{'bbbbbbbbbb':'SubsPlease','cccccccccc':'Erai-raws'})
        self.assertEqual({e['path'] for e in result['candidates']},{str(low),str(other)})
        self.assertTrue(all(e['keep']==str(erai) for e in result['candidates']))
        erai.write_bytes(b'changed video')
        with self.assertRaises(ValueError):clean_duplicate_videos.execute(result)
        self.assertTrue(low.exists());self.assertTrue(other.exists())

    def test_log_audit_counts_failures_without_loading_database(self):
        server=self.base/'server';(server/'log').mkdir(parents=True)
        (server/'log'/'log_20261026.log').write_text('[ERR] [1] Trickplay: Error creating trickplay images.\nSystem.IO.IOException: file is being used by another process.\n',encoding='utf-8')
        result=audit_library.inspect_server(server)
        self.assertEqual(result['trickplay_errors'],1)
        self.assertEqual(result['locked_image_errors'],1)

if __name__ == '__main__':unittest.main()
