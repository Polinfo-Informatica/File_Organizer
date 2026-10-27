"""Delete lower-resolution episode versions and proven hardlink duplicates. No content hashes."""
import argparse
import collections
import json
from pathlib import Path
import re
import uuid
from organize_anime import VIDEO, walk, check_path, within, identity

BASE = Path(__file__).resolve().parent
EPISODE = re.compile(r'^(.*?)\s+-\s+S(\d+)E(\d+)(?:-E(\d+))?\s+-\s+(240|360|480|576|720|1080|1440|2160|4320)p(?:\s|\[|$)', re.I)

def fansub(path, provenance):
    if re.search(r'erai[- _.]*raws', path.name, re.I):
        return 'Erai-raws'
    first = re.match(r'\[([^\]]+)\]', path.name)
    if first and not re.fullmatch(r'[a-f0-9]{8,10}|\d{3,4}p', first[1], re.I):
        return first[1]
    label = re.search(r'\[([a-f0-9]{10})\]', path.stem)
    return provenance.get(label[1]) if label else None

def plan_cleanup(roots, provenance=None):
    provenance = provenance or {}
    roots = [Path(r).absolute() for r in roots]
    files = {}
    groups = collections.defaultdict(list)
    for root in roots:
        check_path(root)
        root = root.resolve(strict=True)
        if not root.is_dir() or root == Path(root.anchor):
            raise ValueError('A named media directory is required')
        for path in walk(root):
            if path.suffix.lower() not in VIDEO:
                continue
            check_path(path)
            path = path.resolve(strict=True)
            if not within(path, root):
                raise ValueError('Media path outside configured root')
            item = {'path': str(path), 'root': str(root), 'identity': identity(path)}
            files[str(path)] = item
            match = EPISODE.match(path.stem)
            if match and item['identity']['size'] > 0:
                title = re.sub(r'\s+', ' ', match[1]).strip().casefold()
                key = (title, int(match[2]), int(match[3]), int(match[4] or match[3]))
                groups[key].append((int(match[5]), str(path)))
    removals = {}
    review = []
    for key, versions in groups.items():
        best = max(res for res, _ in versions)
        best_paths = sorted(path for res, path in versions if res == best)
        preferred = [p for p in best_paths if fansub(Path(p), provenance) == 'Erai-raws']
        keeper = preferred[0] if preferred else best_paths[0]
        if preferred:
            for path in best_paths:
                group = fansub(Path(path), provenance)
                if group and group != 'Erai-raws':
                    removals[path] = {'keep': keeper, 'reason': f'Fansub preference at {best}p: {group} -> Erai-raws'}
        for res, path in versions:
            if res < best:
                removals[path] = {'keep': keeper, 'reason': f'Lower resolution: {res}p -> {best}p'}
    # Only same-file identity proves byte identity without reading/hashing contents.
    links = collections.defaultdict(list)
    for path, item in files.items():
        info = item['identity']
        if path not in removals and info['inode']:
            links[(info['device'], info['inode'])].append(path)
    for paths in links.values():
        paths = sorted(paths)
        for duplicate in paths[1:]:
            if Path(duplicate).samefile(paths[0]):
                removals[duplicate] = {'keep': paths[0], 'reason': 'Identical hardlink'}
    for key, versions in groups.items():
        remaining = [path for _, path in versions if path not in removals]
        if len(remaining) > 1:
            review.append({'episode': list(key), 'files': remaining, 'reason': 'Same resolution; identical content not established'})
    entries = []
    for path, action in removals.items():
        keeper = action['keep']
        visited = {path}
        while keeper in removals:
            if keeper in visited:
                raise ValueError('Invalid deletion dependency')
            visited.add(keeper)
            keeper = removals[keeper]['keep']
        entries.append({**files[path], 'keep': keeper, 'keep_identity': files[keeper]['identity'], 'reason': action['reason']})
    return {'candidates': entries, 'review': review, 'deleted': [], 'errors': []}

def execute(plan):
    for item in plan['candidates']:
        path, keep = Path(item['path']), Path(item['keep'])
        try:
            check_path(path); check_path(keep)
            if not within(path.resolve(strict=True), Path(item['root'])):
                raise ValueError('Deletion outside allowed root')
            if identity(path) != item['identity'] or identity(keep) != item['keep_identity']:
                raise ValueError('Video changed after planning')
            if item['reason'] == 'Identical hardlink' and not path.samefile(keep):
                raise ValueError('Files no longer refer to the same data')
            path.unlink()
            plan['deleted'].append(str(path))
            print(f'Removed: {path.name}\nKept: {keep.name}', flush=True)
        except (OSError, ValueError) as exc:
            plan['errors'].append({'path': str(path), 'error': str(exc)})
            raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    settings = json.loads((BASE/'local_settings.json').read_text(encoding='utf-8-sig'))
    provenance_path = BASE / 'fansub_provenance.json'
    provenance = json.loads(provenance_path.read_text(encoding='utf-8')) if provenance_path.exists() else {}
    plan = plan_cleanup([settings['source'], settings['movies']], provenance)
    logs = BASE/'logs'; logs.mkdir(exist_ok=True)
    report = logs/f'duplicate-videos-{uuid.uuid4().hex}.json'
    report.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Candidates: {len(plan['candidates'])}; uncertain groups: {len(plan['review'])}", flush=True)
    print(f'Report: {report}', flush=True)
    if args.apply:
        try:
            execute(plan)
        finally:
            report.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"Deleted: {len(plan['deleted'])}; errors: {len(plan['errors'])}", flush=True)
    else:
        print('Preview only. Use --apply for permanent deletion.')

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f'ERROR: {exc}')
