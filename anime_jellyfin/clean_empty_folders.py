"""Remove empty directories only, preserving configured media roots."""
import json
import os
from pathlib import Path
import uuid
from organize_anime import check_path, linked, within

BASE = Path(__file__).resolve().parent

def remove_empty(roots, apply=True):
    report = {'candidates': [], 'removed': [], 'errors': []}
    for value in roots:
        root = Path(value).absolute()
        check_path(root)
        root = root.resolve(strict=True)
        if not root.is_dir() or root == Path(root.anchor):
            raise ValueError('A named media directory is required')
        directories = []
        for directory, names, files in os.walk(root, followlinks=False):
            names[:] = [name for name in names if not linked(Path(directory) / name)]
            directories.extend(Path(directory) / name for name in names)
        for path in sorted(directories, key=lambda p: len(p.parts), reverse=True):
            try:
                check_path(path)
                resolved = path.resolve(strict=True)
                if resolved == root or not within(resolved, root):
                    raise ValueError('Directory outside cleanup root')
                if any(str(p) not in report['candidates'] for p in path.iterdir()):
                    continue
                # rmdir refuses nonempty directories, including files created after the check.
                report['candidates'].append(str(path))
                if apply:
                    path.rmdir()
                    report['removed'].append(str(path))
                    print(f'Removed empty directory: {path}', flush=True)
            except FileNotFoundError:
                continue
            except (OSError, ValueError) as exc:
                report['errors'].append({'path': str(path), 'error': str(exc)})
    return report

if __name__ == '__main__':
    settings = json.loads((BASE / 'local_settings.json').read_text(encoding='utf-8-sig'))
    result = remove_empty([settings['source'], settings['movies']])
    logs = BASE / 'logs'
    logs.mkdir(exist_ok=True)
    report_path = logs / f'empty-folders-{uuid.uuid4().hex}.json'
    report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Empty directories removed: {len(result['removed'])}; errors: {len(result['errors'])}")
    print(f'Report: {report_path}')
    print('To restore an empty directory manually, recreate its recorded path in File Explorer.')
