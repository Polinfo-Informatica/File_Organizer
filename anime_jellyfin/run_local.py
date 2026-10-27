"""Central control for the standalone Jellyfin organizer (Python 3.10+)."""
import argparse
import json
import os
from pathlib import Path
import sys
import uuid
import organize_anime as organizer

BASE = Path(__file__).resolve().parent
ACTIONS = ['plan', 'move', 'undo', 'reports', 'images', 'empty', 'duplicates', 'audit', 'settings', 'rules']
LABELS = ['Preview organization', 'Apply latest move plan', 'Undo latest move journal', 'Open reports', 'Delete images and NFO', 'Remove empty directories', 'Review/delete duplicate episode releases', 'Audit media and Jellyfin (read-only)', 'Edit local settings', 'Edit local naming rules']


def menu(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--action', choices=ACTIONS)
    parser.add_argument('--apply', action='store_true', help='Execute the selected modifying action')
    args = parser.parse_args(argv)
    os.chdir(BASE)
    settings_path = BASE / 'local_settings.json'
    if not settings_path.exists():
        if args.action or args.check or args.preview:
            raise ValueError('Create local_settings.json from local_settings.example.json first')
        source = input('Existing Anime directory: ').strip().strip('"')
        movies = input('Existing Movies directory: ').strip().strip('"')
        settings_path.write_text(json.dumps({'source': source, 'target': source, 'movies': movies}, indent=2), encoding='utf-8')
    settings = organizer.load_json(settings_path)
    settings.setdefault('movies', str(Path(settings['source']).parent / 'Movies'))
    roots = [settings['source'], settings['movies']]
    if args.check:
        if sys.version_info < (3, 10) or not all(Path(p).is_dir() for p in roots):
            raise ValueError('Python 3.10+ and both existing media directories are required')
        print('Ready. Python and configured directories verified. No media changed.')
        return
    logs = BASE / 'logs'
    logs.mkdir(exist_ok=True)
    def save(prefix, result):
        path = logs / f'{prefix}-{uuid.uuid4().hex}.json'
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'Report: {path}')
        return path
    def approved(word='APPLY'):
        return args.apply or (not args.action and not args.preview and input(f'Type {word} to proceed: ').strip() == word)
    def latest(name):
        value = (logs / name).read_text(encoding='utf-8').strip()
        if Path(value).name != value or not value:
            raise ValueError('Invalid report pointer')
        return logs / value
    print('Anime Jellyfin Organizer - FAST MOVE / no content hashes / no media backups')
    print(f'Anime: {roots[0]}\nMovies: {roots[1]}')
    if args.action:
        action = args.action
    elif args.preview:
        action = 'plan'
    else:
        for index, label in enumerate(LABELS, 1):
            print(f'{index} - {label}')
        print('0 - Exit')
        choice = input('Option [8]: ').strip() or '8'
        if choice == '0':
            return
        if not choice.isdigit() or not 1 <= int(choice) <= len(ACTIONS):
            raise ValueError('Unknown option')
        action = ACTIONS[int(choice) - 1]
    if action == 'plan':
        plan = logs / f'plan-{uuid.uuid4().hex}.json'
        command = ['plan', '--source', roots[0], '--target', roots[0], '--movies', roots[1], '--output', str(plan)]
        rules = BASE / 'local_rules.json'
        if rules.exists():
            command.extend(['--rules', str(rules)])
        organizer.main(command)
        (logs / 'latest-plan.txt').write_text(plan.name, encoding='utf-8')
        print('Review CSV files and inferred seasons before applying. Existing anime folders only.')
    elif action == 'move':
        plan = latest('latest-plan.txt')
        data = organizer.load_json(plan)
        print(f"Plan: {plan}\nMoves: {len(data['entries'])}; review cases: {len(data['review'])}")
        print('Pause downloads and Jellyfin scans before moving files. No copy fallback.')
        if approved():
            journal = logs / f'journal-{uuid.uuid4().hex}.jsonl'
            (logs / 'latest-journal.txt').write_text(journal.name, encoding='utf-8')
            organizer.main(['apply', '--plan', str(plan), '--journal', str(journal), '--mode', 'move'])
    elif action == 'undo':
        journal = latest('latest-journal.txt')
        if approved('UNDO'):
            organizer.main(['undo', '--journal', str(journal)])
    elif action == 'reports':
        os.startfile(logs)
    elif action == 'images':
        from clean_images_nfo import cleanup
        cleanup(roots, apply=approved('DELETE'))
        print('Generate a fresh move plan after cleanup.')
    elif action == 'empty':
        from clean_empty_folders import remove_empty
        data = remove_empty(roots, apply=approved('DELETE'))
        save('empty-folders', data)
        print(f"Candidates: {len(data['candidates'])}; removed: {len(data['removed'])}; errors: {len(data['errors'])}")
        if data['errors']:
            raise ValueError('Some directories could not be removed; see report')
    elif action == 'duplicates':
        from clean_duplicate_videos import plan_cleanup, execute
        provenance = BASE / 'fansub_provenance.json'
        data = plan_cleanup(roots, organizer.load_json(provenance) if provenance.exists() else {})
        report = save('duplicate-videos', data)
        print(f"Candidates: {len(data['candidates'])}; uncertain groups: {len(data['review'])}")
        print('Highest resolution first; Erai-raws preferred at equal resolution. Unknown ties remain for review.')
        if approved('DELETE'):
            try:
                execute(data)
            finally:
                report.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
                print(f"Deleted: {len(data['deleted'])}; errors: {len(data['errors'])}")
    elif action == 'audit':
        from audit_library import audit, summary
        data = audit(settings)
        save('audit', data)
        print(summary(data))
    elif action in ('settings', 'rules'):
        path = settings_path if action == 'settings' else BASE / 'local_rules.json'
        if not path.exists():
            path.write_text('{"folders": {}, "files": {}}\n', encoding='utf-8')
        os.startfile(path)


if __name__ == '__main__':
    try:
        menu()
    except (OSError, ValueError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
