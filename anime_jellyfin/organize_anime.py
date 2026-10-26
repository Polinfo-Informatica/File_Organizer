#!/usr/bin/env python3
"""Conservative, reversible anime organizer for Jellyfin. Python 3.10+, stdlib only."""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import stat
import uuid
import xml.etree.ElementTree as ET

VIDEO = {'.mkv', '.mp4', '.avi', '.m4v', '.mov', '.webm', '.ts', '.m2ts', '.wmv'}
SIDECAR = {'.srt', '.ass', '.ssa', '.vtt', '.sub', '.idx', '.sup', '.mka', '.aac', '.ac3', '.eac3', '.dts', '.flac'}
SPECIAL = re.compile(r'\b(OVA|OAD|SP|special|movie|NCOP|NCED|OP|ED|PV|trailer|sample)\b', re.I)
MARKER = re.compile(r'(?<!\w)S(?P<s>\d{1,3})E(?P<e>\d{1,4})(?:-?E?(?P<end>\d{1,4}))?(?![\w]|\.\d{1,2}(?!\d))', re.I)
RAW = re.compile(r'^(?P<title>.+?)\s+-\s+(?P<e>\d{1,4})(?:v\d+)?(?:\s*-\s*(?P<end>\d{1,4}))?\s*(?:\([^)]*\)\s*)*$', re.I)
SEASON = re.compile(r'^(.*?)\s+(?:S(\d{1,3})|Season\s+(\d{1,3})|(\d{1,3})(?:st|nd|rd|th)\s+Season)\s*$', re.I)
ROMAN = {'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6}

def safe_name(value):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', ' ', value)
    value = re.sub(r'\s+', ' ', value).strip().rstrip('.')
    if not value or re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', value, re.I):
        raise ValueError('Invalid series name')
    return value

def linked(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return path.is_symlink() or bool(getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))

def check_path(path):
    for parent in (path, *path.parents):
        if linked(parent):
            raise ValueError(f'Symlink/junction is not supported: {parent}')

def within(path, root):
    return path == root or root in path.parents

def walk(root, skip_trickplay=True):
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if (not skip_trickplay or not d.endswith('.trickplay')) and not linked(Path(directory) / d))
        for name in sorted(files):
            p = Path(directory) / name
            if not linked(p):
                yield p

def parse_name(path, root, allow_ambiguous=False):
    """Return a candidate only; catalog season ordering still needs review."""
    bracketed = re.match(r'^\[[^\]]+\]\[(?P<title>[^\]]+)\]\[(?P<e>\d{1,4})\]', path.stem)
    if bracketed:
        text = f"{bracketed['title']} - {bracketed['e']}"
    else:
        text = re.sub(r'\[[^\]]*\]', '', path.stem).strip()
    match = MARKER.search(text)
    if match:
        title = text[:match.start()].strip(' ._-').replace('.', ' ')
        if not title:
            title = path.parent.name
        return title, int(match['s']), int(match['e']), int(match['end'] or match['e']), 'explicit SxxExx'
    if SPECIAL.search(text) or re.search(r'\d+\.\d+', text):
        raise ValueError('Special/movie/fractional episode requires a file rule')
    if not allow_ambiguous and (re.search(r'\s+-\s+.*\b(?:hen|arc|part)\b', text, re.I) or re.search(r'-hen\b', text, re.I)):
        raise ValueError('Named arc/part requires a catalog mapping')
    match = RAW.fullmatch(text)
    if not match:
        raise ValueError('Unrecognized filename; add a file rule')
    title = match['title'].strip()
    episode, end = int(match['e']), int(match['end'] or match['e'])
    season = None
    sm = SEASON.fullmatch(title)
    if sm:
        title, season = sm[1], int(next(x for x in sm.groups()[1:] if x))
    else:
        rm = re.fullmatch(r'(.+?)\s+(II|III|IV|V|VI)', title)
        if rm:
            title, season = rm[1], ROMAN[rm[2]]
    # A named Season folder can supply season information, but never override a conflict.
    for parent in path.relative_to(root).parts[:-1]:
        pm = re.fullmatch(r'Season\s+(\d{1,3})', parent, re.I)
        if pm:
            ps = int(pm[1])
            if season is not None and ps != season:
                raise ValueError('Conflicting season markers; add a file rule')
            season = ps
    if not episode:
        raise ValueError('Episode zero requires an explicit special mapping')
    if not allow_ambiguous and season is None and (episode > 50 or re.search(r'\s\d+$', title)):
        raise ValueError('Possible absolute numbering or numbered sequel; add a rule')
    note = 'season marker inferred; verify catalog order' if season is not None else 'season 1 assumed; verify catalog order'
    return title, season if season is not None else 1, episode, end, note

def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)

def snapshot(path):
    stat = path.stat()
    return {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def inventory(root):
    result = collections.Counter()
    existing_metadata = []
    for path in walk(root, skip_trickplay=False):
        relative = path.relative_to(root)
        ext = path.suffix.lower()
        if any(part.endswith('.trickplay') for part in relative.parts):
            kind = 'jellyfin_trickplay'
        elif ext in VIDEO:
            kind = 'video'
        elif ext in SIDECAR:
            kind = 'external_subtitle_or_audio'
        elif ext == '.nfo':
            kind = 'jellyfin_nfo'
            if path.name.lower() == 'tvshow.nfo' and path.stat().st_size < 2_000_000:
                try:
                    xml = ET.parse(path).getroot()
                    existing_metadata.append({'path': str(relative), 'title': xml.findtext('title'),
                        'ids': {tag: xml.findtext(tag) for tag in ('tmdbid', 'tvdbid', 'imdbid') if xml.findtext(tag)},
                        'uniqueids': [{'type': n.get('type'), 'value': n.text} for n in xml.findall('uniqueid')]})
                except (ET.ParseError, OSError):
                    pass
        elif ext in {'.jpg', '.jpeg', '.png', '.webp', '.svg'}:
            kind = 'artwork_or_thumbnail'
        elif ext in {'.torrent', '.part', '.!qb', '.!ut'}:
            kind = 'torrent_or_incomplete'
        else:
            kind = 'other_untouched'
        result[kind] += 1
    return {'counts': dict(result), 'existing_series_metadata_for_review_only': existing_metadata}

def make_plan(root, target, rules=None):
    root, target = Path(root).absolute(), Path(target).absolute()
    check_path(root); check_path(target)
    root, target = root.resolve(), target.resolve()
    if not root.is_dir() or within(root, target) or within(target, root):
        raise ValueError('Source must exist; use separate non-nested source and destination roots')
    rules = rules or {}
    files = list(walk(root))
    by_folder = collections.defaultdict(list)
    for p in files:
        by_folder[p.parent].append(p)
    entries, review = [], []
    def add(source, dest, kind, note):
        entries.append({'source': str(source), 'destination': str(dest), 'kind': kind, 'note': note, **snapshot(source)})
    for video in (p for p in files if p.suffix.lower() in VIDEO):
        rel = video.relative_to(root).as_posix()
        rule = rules.get('files', {}).get(rel)
        try:
            if rule and rule.get('skip'):
                raise ValueError('File skipped by rule')
            if rule and rule.get('type') == 'movie':
                title = safe_name(rule['title'])
                if rule.get('year'):
                    title += f" ({int(rule['year'])})"
                provider = rule.get('provider_id')
                if provider:
                    if not re.fullmatch(r'(?:tmdbid-\d+|imdbid-tt\d+)', provider):
                        raise ValueError('Invalid movie provider identifier')
                    title += f' [{provider}]'
                folder = target / 'Movies' / title
                stem = title
                note = 'explicit movie rule'
            elif rule:
                title, season, ep = rule['series'], int(rule['season']), int(rule['episode'])
                end, note = int(rule.get('end_episode', ep)), 'explicit file rule'
            else:
                folder_rule = rules.get('folders', {}).get(video.relative_to(root).parts[0], {})
                if folder_rule.get('skip'):
                    raise ValueError('Folder skipped by rule')
                title, season, ep, end, note = parse_name(video, root, allow_ambiguous='season' in folder_rule)
                title = folder_rule.get('series', title)
                season = int(folder_rule.get('season', season))
                ep += int(folder_rule.get('episode_offset', 0))
                end += int(folder_rule.get('episode_offset', 0))
            if not (rule and rule.get('type') == 'movie'):
                title = safe_name(title)
                if rule:
                    provider = rule.get('provider_id')
                else:
                    provider = folder_rule.get('provider_id')
                if provider:
                    if not re.fullmatch(r'(?:tmdbid-\d+|tvdbid-\d+|imdbid-tt\d+)', provider):
                        raise ValueError('Invalid metadata provider identifier')
                    title += f' [{provider}]'
                if not 0 <= season <= 999 or not 1 <= ep <= end <= 9999:
                    raise ValueError('Invalid season/episode mapping')
                code = f'S{season:02d}E{ep:02d}' + (f'-E{end:02d}' if end > ep else '')
                folder = target / 'Shows' / title / f'Season {season:02d}'
                quality_match = re.search(r'(?<!\d)(\d{3,4}[pi])(?!\w)', video.name, re.I)
                quality = quality_match[1].lower() if quality_match else 'original'
                release = hashlib.sha256(rel.encode('utf-8')).hexdigest()[:10]
                stem = f'{title} - {code} - {quality} [{release}]'
            add(video, folder / (stem + video.suffix.lower()), 'video', note)
            for companion in by_folder[video.parent]:
                suffix = companion.name[len(video.stem):]
                same_base = companion.stem == video.stem or companion.stem.casefold().startswith(video.stem.casefold() + '.')
                if (companion.suffix.lower() in SIDECAR and same_base) or (companion.name.casefold().startswith(video.stem.casefold()) and suffix.lower() in ('-thumb.jpg', '-thumb.png')):
                    add(companion, folder / (stem + suffix), 'companion', 'matched exact video basename')
        except (ValueError, KeyError) as exc:
            review.append({'source': rel, 'reason': str(exc)})
    # A collision blocks every member, including companions of conflicting videos.
    counts = collections.Counter(e['destination'].casefold() for e in entries)
    source_counts = collections.Counter(e['source'].casefold() for e in entries)
    bad = {e['source'] for e in entries if counts[e['destination'].casefold()] > 1 or source_counts[e['source'].casefold()] > 1}
    if bad:
        # Keep collision handling fail-closed for the complete plan.
        review.extend({'source': s, 'reason': 'Destination/source collision: select one release or map explicitly'} for s in sorted(bad))
    return {'version': 1, 'source_root': str(root), 'target_root': str(target), 'blocked': bool(bad), 'entries': entries, 'review': review,
            'inventory': inventory(root), 'notice': 'Filename syntax is standardized. Verify series identity and episode order against the Jellyfin metadata provider. NFO, shared artwork and trickplay are left in the source.'}

def append_journal(path, row):
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())

def exclusive_copy(source, destination):
    with source.open('rb') as src, destination.open('xb') as dst:
        shutil.copyfileobj(src, dst, 8 * 1024 * 1024)
    shutil.copystat(source, destination)

def validate_plan(plan):
    if plan.get('version') != 1 or plan.get('blocked'):
        raise ValueError('Unsupported or blocked plan')
    source_root, target_root = Path(plan['source_root']).resolve(), Path(plan['target_root']).resolve()
    if within(source_root, target_root) or within(target_root, source_root):
        raise ValueError('Overlapping roots')
    targets, sources = set(), set()
    for e in plan['entries']:
        src, dst = Path(e['source']), Path(e['destination'])
        check_path(src); check_path(dst)
        if not src.is_absolute() or not dst.is_absolute() or not within(src.resolve(), source_root) or not within(dst.resolve(), target_root):
            raise ValueError('Path escapes plan roots')
        sk, dk = str(src.resolve()).casefold(), str(dst.resolve()).casefold()
        if sk in sources or dk in targets or dst.exists():
            raise ValueError(f'Duplicate path or existing destination: {dst}')
        sources.add(sk); targets.add(dk)
        if not src.is_file() or snapshot(src) != {k: e[k] for k in ('size', 'mtime_ns')}:
            raise ValueError(f'Source changed; regenerate plan: {src}')

def apply(plan, journal, mode='hardlink'):
    validate_plan(plan)
    journal = Path(journal).absolute()
    journal.parent.mkdir(parents=True, exist_ok=True)
    with journal.open('x', encoding='utf-8'):
        pass
    for e in plan['entries']:
        src, dst = Path(e['source']), Path(e['destination'])
        check_path(src); check_path(dst)
        if snapshot(src) != {k: e[k] for k in ('size', 'mtime_ns')}:
            raise ValueError(f'Source changed during apply: {src}')
        sha = digest(src)
        operation = 'copy' if e['kind'] != 'video' and mode == 'hardlink' else mode
        row = {'id': uuid.uuid4().hex, 'state': 'prepared', 'operation': operation, 'source': str(src), 'destination': str(dst), 'sha256': sha}
        append_journal(journal, row)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if operation == 'hardlink':
            os.link(src, dst)
        elif operation in ('copy', 'move'):
            exclusive_copy(src, dst)
        else:
            raise ValueError('Unknown operation')
        if digest(dst) != sha or snapshot(src) != {k: e[k] for k in ('size', 'mtime_ns')}:
            raise ValueError(f'File changed or copy verification failed; inspect journal: {journal}')
        if operation == 'move':
            src.unlink()
        row['state'] = 'completed'
        append_journal(journal, row)
        print(f'{operation}: {dst}')
    return journal

def undo(journal):
    journal = Path(journal)
    rows = [json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines() if line.strip()]
    completed = {r['id'] for r in rows if r['state'] == 'completed'}
    undone = {r['id'] for r in rows if r['state'] == 'undone'}
    pending = [r for r in rows if r['state'] == 'prepared' and r['id'] not in completed]
    if pending:
        print('WARNING: interrupted operations exist. Inspect prepared records manually; they are not automatically undone.')
    for row in reversed(rows):
        if row['state'] != 'completed' or row['id'] in undone:
            continue
        src, dst = Path(row['source']), Path(row['destination'])
        check_path(src); check_path(dst)
        if not dst.is_file() or digest(dst) != row['sha256']:
            raise ValueError(f'Destination missing or changed; refusing undo: {dst}')
        if row['operation'] == 'move':
            if src.exists():
                raise ValueError(f'Original path occupied: {src}')
            src.parent.mkdir(parents=True, exist_ok=True)
            exclusive_copy(dst, src)
            if digest(src) != row['sha256']:
                raise ValueError('Restore verification failed')
            dst.unlink()
        elif row['operation'] in ('copy', 'hardlink'):
            if not src.is_file() or digest(src) != row['sha256']:
                raise ValueError(f'Original missing or changed; refusing to delete destination: {src}')
            dst.unlink()
        else:
            raise ValueError('Unknown journal operation')
        row['state'] = 'undone'
        append_journal(journal, row)
        undone.add(row['id'])
        print(f'undone: {dst}')

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    plan = commands.add_parser('plan', help='Read filenames and save a preview; do not change media')
    plan.add_argument('--source', required=True)
    plan.add_argument('--target', required=True)
    plan.add_argument('--rules')
    plan.add_argument('--output', default='logs/plan.json')
    execute = commands.add_parser('apply')
    execute.add_argument('--plan', required=True)
    execute.add_argument('--journal', default=None)
    execute.add_argument('--mode', choices=['hardlink', 'copy', 'move'], default='hardlink')
    revert = commands.add_parser('undo')
    revert.add_argument('--journal', required=True)
    args = parser.parse_args(argv)
    if args.command == 'plan':
        result = make_plan(args.source, args.target, load_json(args.rules) if args.rules else None)
        output = Path(args.output).absolute()
        save_json(output, result)
        preview = output.with_suffix('.csv')
        with preview.open('x', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['source', 'destination', 'kind', 'note'])
            writer.writeheader()
            writer.writerows({k: e[k] for k in writer.fieldnames} for e in result['entries'])
        review_path = output.with_name(output.stem + '-review.csv')
        with review_path.open('x', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['source', 'reason'])
            writer.writeheader()
            writer.writerows(result['review'])
        print(f"Inventory: {result['inventory']['counts']}")
        print(f"Planned files: {len(result['entries'])}; review items: {len(result['review'])}; blocked: {result['blocked']}")
        print(f'Plan: {output}\nPreview: {preview}')
    elif args.command == 'apply':
        journal = args.journal or str(Path(args.plan).parent / f'journal-{uuid.uuid4().hex}.jsonl')
        print(f'Journal: {journal}', flush=True)
        apply(load_json(args.plan), journal, args.mode)
    else:
        undo(args.journal)
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
