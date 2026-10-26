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
        target = input('Separate Jellyfin output directory: ').strip().strip('"')
        settings_path.write_text(json.dumps({'source': source, 'target': target}, indent=2), encoding='utf-8')
    settings = organizer.load_json(settings_path)
    logs = BASE / 'logs'
    logs.mkdir(exist_ok=True)
    print('Anime Jellyfin Organizer')
    print('1 - Generate preview (no media changes)')
    print('2 - Apply the latest preview using hardlinks')
    print('3 - Undo the latest journal')
    print('4 - Open the reports directory')
    choice = input('Option [1]: ').strip() or '1'
    if choice == '1':
        plan = logs / f'plan-{uuid.uuid4().hex}.json'
        args = ['plan', '--source', settings['source'], '--target', settings['target'], '--output', str(plan)]
        rules = BASE / 'local_rules.json'
        if rules.exists():
            args.extend(['--rules', str(rules)])
        organizer.main(args)
        (logs / 'latest-plan.txt').write_text(str(plan), encoding='utf-8')
        print('Review the preview CSV, review CSV, and inferred season notes before applying.')
    elif choice == '2':
        plan = Path((logs / 'latest-plan.txt').read_text(encoding='utf-8'))
        p = organizer.load_json(plan)
        print(f"Preview: {plan}")
        print(f"Files: {len(p['entries'])}; unprocessed review cases: {len(p['review'])}")
        print('Source videos stay in place. Hardlinks require the same NTFS volume.')
        print('Only completed downloads should be processed. Catalog episode ordering must be reviewed.')
        if input('Type APPLY to proceed: ').strip() != 'APPLY':
            return
        journal = logs / f'journal-{uuid.uuid4().hex}.jsonl'
        (logs / 'latest-journal.txt').write_text(str(journal), encoding='utf-8')
        organizer.main(['apply', '--plan', str(plan), '--journal', str(journal)])
    elif choice == '3':
        journal = (logs / 'latest-journal.txt').read_text(encoding='utf-8')
        print(f'Journal: {journal}')
        if input('Type UNDO to proceed: ').strip() == 'UNDO':
            organizer.main(['undo', '--journal', journal])
    elif choice == '4':
        os.startfile(logs)
    else:
        raise ValueError('Unknown option')

if __name__ == '__main__':
    try:
        menu()
    except (OSError, ValueError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
