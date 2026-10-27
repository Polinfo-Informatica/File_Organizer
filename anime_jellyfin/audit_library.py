"""Read-only media/configuration audit; never read or hash video contents."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import os
import re
import xml.etree.ElementTree as ET
from organize_anime import VIDEO, check_path, linked
from clean_images_nfo import DELETE_EXTENSIONS

FLAGS = ['EnableChapterImageExtraction', 'ExtractChapterImagesDuringLibraryScan', 'EnableTrickplayImageExtraction', 'ExtractTrickplayImagesDuringLibraryScan', 'SaveLocalMetadata', 'SaveTrickplayWithMedia', 'EnableEmbeddedTitles', 'EnableEmbeddedEpisodeInfos', 'EnableRealtimeMonitor']
EPISODE = re.compile(r'^(.*?)\s*-\s*S(\d+)E(\d+)(?:-E(\d+))?', re.I)


def inspect_media(value, anime=False):
    root = Path(value).absolute()
    check_path(root)
    if not root.is_dir() or root == Path(root.anchor):
        raise ValueError(f'Existing named media directory required: {root}')
    result = dict(root=str(root), videos=0, extensions={}, images_nfo=[], empty_directories=[], nested_videos=[], nonstandard_episodes=[], zero_byte_videos=[], auxiliary_files=[], duplicate_episode_groups=[], errors=[])
    counts, groups = Counter(), defaultdict(list)
    def error(exc):
        result['errors'].append(str(exc))
    for directory, names, files in os.walk(root, followlinks=False, onerror=error):
        names[:] = [n for n in names if not linked(Path(directory) / n)]
        if not names and not files and Path(directory) != root:
            result['empty_directories'].append(str(Path(directory).relative_to(root)))
        for name in files:
            path = Path(directory) / name
            if linked(path):
                continue
            relative = str(path.relative_to(root))
            extension = path.suffix.lower()
            counts[extension] += 1
            if extension in VIDEO:
                result['videos'] += 1
                try:
                    if path.stat().st_size == 0:
                        result['zero_byte_videos'].append(relative)
                except OSError as exc:
                    error(exc)
                if len(path.relative_to(root).parts) > 2:
                    result['nested_videos'].append(relative)
                match = EPISODE.match(path.stem)
                if anime and not match:
                    result['nonstandard_episodes'].append(relative)
                if match:
                    key = (re.sub(r'\s+', ' ', match[1]).strip().casefold(), int(match[2]), int(match[3]), int(match[4] or match[3]))
                    groups[key].append(relative)
            elif extension in DELETE_EXTENSIONS:
                result['images_nfo'].append(relative)
            else:
                result['auxiliary_files'].append(relative)
    result['extensions'] = dict(counts)
    result['duplicate_episode_groups'] = [dict(episode=list(k), files=v) for k, v in groups.items() if len(v) > 1]
    return result


def inspect_server(value):
    server = Path(value)
    result = dict(path=str(server), libraries=[], latest_log=None, trickplay_errors=0, locked_image_errors=0, missing_path_errors=0, database_error_lines=0, error_categories={}, errors=[])
    try:
        for path in sorted((server / 'root' / 'default').glob('*/options.xml')):
            tree = ET.parse(path).getroot()
            result['libraries'].append(dict(name=path.parent.name, paths=[e.text for e in tree.findall('./PathInfos/MediaPathInfo/Path')], flags={name: tree.findtext(name) for name in FLAGS}, metadata_savers=[e.text for e in tree.findall('./MetadataSavers/string')]))
        logs = sorted((server / 'log').glob('log_*.log'), key=lambda p: p.stat().st_mtime, reverse=True)
        if logs:
            path = logs[0]
            result['latest_log'] = str(path)
            counts = Counter()
            # Stream logs; no media data or Jellyfin database is read.
            with path.open(encoding='utf-8-sig', errors='replace') as stream:
                for line in stream:
                    if '[ERR]' in line:
                        match = re.search(r'\[ERR\]\s+\[\d+\]\s+([^:]+):', line)
                        counts[match[1] if match else 'Other'] += 1
                    result['trickplay_errors'] += int('Error creating trickplay images.' in line)
                    result['locked_image_errors'] += int('System.IO.IOException:' in line and 'being used by another process' in line)
                    result['missing_path_errors'] += int('System.IO.FileNotFoundException:' in line or 'System.IO.DirectoryNotFoundException:' in line)
                    result['database_error_lines'] += int('[ERR]' in line and 'Microsoft.EntityFrameworkCore' in line)
            result['error_categories'] = dict(counts)
    except (OSError, ET.ParseError) as exc:
        result['errors'].append(str(exc))
    return result


def audit(settings):
    return dict(created_utc=datetime.now(timezone.utc).isoformat(), anime=inspect_media(settings['source'], anime=True), movies=inspect_media(settings['movies']), jellyfin=inspect_server(settings.get('jellyfin_server', r'C:\ProgramData\Jellyfin\Server')), notes=[
        'Nonstandard names and matching episode numbers are review candidates, not proof of bad media or identical content.',
        'Disable local NFO saving if media folders must remain free of regenerated NFO files.',
        'Consider disabling chapter/trickplay extraction during library scans; logs can identify actual extraction failures.',
        'Do not delete Jellyfin databases or metadata directories as routine cleanup. Rescan after moving media.',
        'External MKA audio and SRT/ASS subtitles are media companions, not junk.',
        'No media was moved, copied, deleted, hashed, decoded, or transcoded by this audit.'])


def summary(data):
    lines = ['READ-ONLY AUDIT']
    for label in ('anime', 'movies'):
        row = data[label]
        lines.append(f"{label}: {row['videos']} videos; {len(row['images_nfo'])} images/NFO; {len(row['empty_directories'])} empty directories; {len(row['nested_videos'])} nested videos; {len(row['nonstandard_episodes'])} names to review; {len(row['duplicate_episode_groups'])} matching episode groups; {len(row['zero_byte_videos'])} zero-byte videos")
    server = data['jellyfin']
    lines.append(f"Latest log: {server['latest_log']}")
    lines.append(f"Trickplay errors: {server['trickplay_errors']}; file-in-use errors: {server['locked_image_errors']}; missing-path exceptions: {server['missing_path_errors']}; database error lines: {server['database_error_lines']}")
    for library in server['libraries']:
        if any(str(p).casefold() in [data['anime']['root'].casefold(), data['movies']['root'].casefold()] for p in library['paths']):
            lines.append(f"{library['name']}: " + ', '.join(f'{k}={v}' for k,v in library['flags'].items()))
    lines.extend(data['notes'])
    return '\n'.join(lines)
