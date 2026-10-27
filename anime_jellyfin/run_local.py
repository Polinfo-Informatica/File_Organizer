#!/usr/bin/env python3
"""Windows menu for read-only planning, deliberate apply and journal-based undo."""
import json
import os
from pathlib import Path
import sys
import uuid
import organize_anime as organizer

BASE = Path(__file__).resolve().parent

def menu():
    os.chdir(BASE)
    settings_path = BASE / 'local_settings.json'
    if not settings_path.exists():
        source = input('Source directory: ').strip().strip('"')
        target = source
        settings_path.write_text(json.dumps({'source': source, 'target': target}, indent=2), encoding='utf-8')
    settings = organizer.load_json(settings_path)
    if '--check' in sys.argv:
        if sys.version_info < (3, 10):
            raise ValueError('Python 3.10 or newer is required')
        if not Path(settings['source']).is_dir():
            raise ValueError('Configured source directory was not found')
        print('Ready. Python and configured source directory verified. No media changed.')
        return
    logs = BASE / 'logs'
    logs.mkdir(exist_ok=True)
    print('Anime Jellyfin Organizer - FAST MOVE (no content hashes)')
    print(f"Download root: {settings['source']}")
    print('Episodes stay directly in their existing anime folders.')
    print(f"Movies folder: {settings.get('movies', str(Path(settings['source']).parent / 'Movies'))}")
    print('1 - Generate preview (no media changes)')
    print('2 - Apply the latest preview using fast same-drive moves')
    print('3 - Undo the latest journal')
    print('4 - Open the reports directory')
    print('5 - Delete images and NFO in Anime and Movies')
    choice = '1' if '--preview' in sys.argv else (input('Option [1]: ').strip() or '1')
    if choice == '1':
        plan = logs / f'plan-{uuid.uuid4().hex}.json'
        args = ['plan', '--source', settings['source'], '--target', settings['source'], '--movies', settings.get('movies', str(Path(settings['source']).parent / 'Movies')), '--output', str(plan)]
        rules = BASE / 'local_rules.json'
        if rules.exists():
            args.extend(['--rules', str(rules)])
        organizer.main(args)
        (logs / 'latest-plan.txt').write_text(plan.name, encoding='utf-8')
        print('Review the preview CSV, review CSV, and inferred season notes before applying.')
    elif choice == '2':
        plan = logs / (logs / 'latest-plan.txt').read_text(encoding='utf-8').strip()
        p = organizer.load_json(plan)
        print(f"Preview: {plan}")
        print(f"Files: {len(p['entries'])}; unprocessed review cases: {len(p['review'])}")
        print('Files will be MOVED on the same filesystem without copying video data.')
        print('Torrent paths will change. Pause downloads and review catalog episode ordering.')
        if input('Type APPLY to proceed: ').strip() != 'APPLY':
            return
        journal = logs / f'journal-{uuid.uuid4().hex}.jsonl'
        (logs / 'latest-journal.txt').write_text(journal.name, encoding='utf-8')
        organizer.main(['apply', '--plan', str(plan), '--journal', str(journal), '--mode', 'move'])
    elif choice == '3':
        journal = str(logs / (logs / 'latest-journal.txt').read_text(encoding='utf-8').strip())
        print(f'Journal: {journal}')
        if input('Type UNDO to proceed: ').strip() == 'UNDO':
            organizer.main(['undo', '--journal', journal])
    elif choice == '4':
        os.startfile(logs)
    elif choice == '5':
        from clean_images_nfo import cleanup
        cleanup([settings['source'], settings.get('movies', str(Path(settings['source']).parent / 'Movies'))], apply=True)
        print('Generate a fresh preview after cleanup before applying moves.')
    else:
        raise ValueError('Unknown option')

if __name__ == '__main__':
    try:
        menu()
    except (OSError, ValueError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
