#!/usr/bin/env python3
"""Delete only image and NFO files from explicitly configured media roots."""
import argparse
import json
from pathlib import Path
import sys
import uuid
from organize_anime import check_path, within, walk, snapshot

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.jpe', '.jfif', '.png', '.webp', '.gif', '.bmp', '.tif', '.tiff', '.avif', '.heic', '.heif', '.ico', '.svg'}
DELETE_EXTENSIONS = IMAGE_EXTENSIONS | {'.nfo'}
BASE = Path(__file__).resolve().parent

def candidates(roots):
    found = []
    seen = set()
    for raw in roots:
        root = Path(raw).absolute()
        check_path(root)
        root = root.resolve(strict=True)
        if not root.is_dir() or root == Path(root.anchor):
            raise ValueError('A named media directory is required; drive roots are forbidden')
        for path in walk(root, skip_trickplay=False):
            if path.suffix.lower() not in DELETE_EXTENSIONS:
                continue
            check_path(path)
            resolved = path.resolve(strict=True)
            if not within(resolved, root):
                raise ValueError('Cleanup path escapes the configured media directory')
            key = str(resolved).casefold()
            if key not in seen:
                seen.add(key)
                found.append({'path': str(resolved), 'root': str(root), **snapshot(resolved)})
    return found

def cleanup(roots, apply=False):
    entries = candidates(roots)
    logs = BASE / 'logs'
    logs.mkdir(exist_ok=True)
    report = logs / f'cleanup-{uuid.uuid4().hex}.json'
    data = {'roots': [str(r) for r in roots], 'planned': entries, 'deleted': [], 'error': None}
    report.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Images/NFO selected: {len(entries)}; bytes: {sum(e["size"] for e in entries)}', flush=True)
    print(f'Report: {report}', flush=True)
    if not apply:
        print('Preview only. Use --apply to delete these image/NFO files.')
        return data
    try:
        for index, entry in enumerate(entries, 1):
            path = Path(entry['path'])
            check_path(path)
            if not within(path.resolve(), Path(entry['root'])) or path.suffix.lower() not in DELETE_EXTENSIONS:
                raise ValueError('Cleanup boundary check failed')
            if not path.exists():
                continue
            if snapshot(path) != {k: entry[k] for k in ('size', 'mtime_ns')}:
                raise ValueError(f'File changed during cleanup: {path}')
            path.unlink()
            data['deleted'].append(str(path))
            if index % 100 == 0:
                print(f'Images/NFO removed: {index}/{len(entries)}', flush=True)
    except (OSError, ValueError) as exc:
        data['error'] = str(exc)
        raise
    finally:
        report.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'Deleted: {len(data["deleted"])}. Videos and subtitles were excluded.', flush=True)
    return data

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    settings = json.loads((BASE / 'local_settings.json').read_text(encoding='utf-8-sig'))
    cleanup([settings['source'], settings.get('movies', str(Path(settings['source']).parent / 'Movies'))], args.apply)

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
