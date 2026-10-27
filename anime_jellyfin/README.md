# Anime Jellyfin Organizer

Python 3.10+, standard library only. Default mode: direct same-filesystem MOVE. No video copies, transcoding or file-content hashes.

## Required layout

Episodes stay directly in their EXISTING top-level anime folders:

    Anime/Existing Anime Name/Series - S02E03 - 1080p [release-id].mkv

The app never creates Shows, Movies, Season folders, or new anime folders inside Anime. The existing parent folder is preserved even if its name differs from the release title. Loose episodes require a unique matching existing anime folder or a rule with folder set to an existing folder name; otherwise they remain for review.

Movies go directly into the separate EXISTING movies directory, normally the sibling Movies directory. It must exist and may not be inside Anime. Explicit movie rules and clear '- Movie' release markers are supported. Uncertain movies/specials remain for review rather than receiving arbitrary episode numbers.

Old previews using the previous layout are rejected. Generate a fresh preview.

## Windows menu

Open Run.cmd, or INICIAR.cmd in the customized local package.

1. Generate a preview without changing media.
2. Apply fast moves after typing APPLY.
3. Undo the latest move journal after typing UNDO.
4. Open reports.
5. Delete images and NFO recursively in the configured Anime and Movies roots.

Local settings contain source, target (identical to source), and movies paths. Local rules and reports stay out of Git. The customized local package also has LIMPAR_IMAGENS_NFO.cmd for one-click cleanup.

CLI:

    python organize_anime.py plan --source "D:\Videos\Anime" --movies "D:\Videos\Movies" --output "logs\plan.json"
    python organize_anime.py apply --plan "logs\plan.json"
    python organize_anime.py undo --journal "logs\journal-ID.jsonl"
    python clean_images_nfo.py --apply

Use a fresh output filename for each preview. Generate a NEW preview after deleting companions, before applying moves.

## Image/NFO cleanup

Deletes only .nfo and image extensions, including JPG/JPEG/PNG/WebP/GIF/BMP/TIFF/AVIF/HEIC/ICO/SVG. Image files inside trickplay are included. Videos, subtitles, other file types and directories are excluded. Symlinks/junctions are skipped and each path is checked against the explicit roots. A report lists selected/deleted paths and failures.

Deletion is permanent and has no app undo. The cleanup report is a log, not a content backup. Restore deleted assets from a separate backup or let Jellyfin regenerate metadata and artwork. Pause metadata/image generation if you need the folders to remain free of regenerated assets. No empty-directory cleanup is performed.

## Naming and catalog rules

Supports S01E02, dash episode numbers, ranges, v2, season suffixes, roman numerals II through VI, bracketed releases and Unicode. A deterministic filename-path label preserves multiple releases; it does not read video contents. Only exact-basename companions follow a video. NFO and shared artwork are left unchanged by organization itself; use cleanup to remove them.

Names cannot prove catalog episode ordering. Inferred seasons are marked in preview notes. Absolute numbering, named arcs, specials and ambiguous patterns can require explicit mappings. TMDB and TVDB may use different season orders.

Copy rules.example.json to local_rules.json. Folder rules support series, season, episode_offset, provider_id and folder (an existing direct anime folder). File rules take precedence and support series/season/episode/end_episode/provider_id/folder, or type=movie with title/year/provider_id. skip=true excludes an item. Use verified identifiers and special episode numbers.

## Checks and undo

Moves use file identity, size and modification time, not content hashes. Metadata checks cannot detect changes that preserve those attributes. Cross-filesystem moves are refused; there is no automatic copy fallback. Torrent paths change after moving.

Destinations are never overwritten. Journals record prepared/completed moves. Undo renames completed moves back and refuses changed identities or occupied source paths. Old copy/hardlink journals require matching originals for safe automated undo. Interrupted prepared records require manual inspection.

Manual reversal: use each completed journal entry to return the destination to its original path only if that path is free. Preserve originals before removing old linked/copied output. Keep logs and app backups. Empty folders may remain. Cleanup deletions are separate from move journals and cannot be undone by option 3.

## Tests

    python -m unittest discover -s . -v

Tests cover existing-folder layout, rejection of nested/old destinations, movies routing, no-copy moves and undo, re-running previews, naming, conflicts, Unicode, metadata association, and cleanup preserving videos/subtitles. Hardlink integration may be skipped when host permissions deny it.
