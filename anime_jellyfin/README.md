# Anime Jellyfin Organizer

Python 3.10+, standard library only. Default mode: direct same-filesystem MOVE. No video copies, transcoding or file-content hashes.

## Required layout

Episodes stay directly in their EXISTING top-level anime folders:

    Anime/Existing Anime Name/Series - S02E03 - 1080p [release-id].mkv

The app never creates Shows, Movies, Season folders, or new anime folders inside Anime. The existing parent folder is preserved even if its name differs from the release title. Loose episodes require a unique matching existing anime folder or a rule with folder set to an existing folder name; otherwise they remain for review.

Movies go directly into the separate EXISTING movies directory, normally the sibling Movies directory. It must exist and may not be inside Anime. Explicit movie rules and clear '- Movie' release markers are supported. Uncertain movies/specials remain for review rather than receiving arbitrary episode numbers.

Old previews using the previous layout are rejected. Generate a fresh preview.

## Central Windows control

Open INICIAR.cmd (Run.cmd is an alias). The complete package uses Python 3.10+ and only the standard library. No pip installation is needed.

1. Preview organization.
2. Apply the latest preview with same-drive moves.
3. Undo the latest move journal.
4. Open reports.
5. Delete images and NFO in both configured media roots.
6. Remove empty directories without removing the media roots.
7. Preview/delete duplicate episode releases.
8. Audit media folders, Jellyfin library settings and the latest server log (read-only; default).
9. Edit local settings.
10. Edit local naming rules.

The one-off Tensei correction is intentionally not part of this tool.

On first interactive launch, enter existing Anime and Movies paths. For unattended use, copy local_settings.example.json to local_settings.json and edit the paths. The customized package already has the user's paths, rules and fansub provenance. These private files are excluded from Git. Source and target are the same directory; movies must use a separate existing directory.

CLI examples:

    python run_local.py --check
    python run_local.py --action audit
    python run_local.py --action plan
    python run_local.py --action move --apply
    python run_local.py --action duplicates
    python run_local.py --action duplicates --apply
    python run_local.py --action images --apply
    python run_local.py --action empty --apply

Without --apply, modifying CLI actions do not execute. The interactive menu requests APPLY, DELETE or UNDO for modifying actions. Legacy cleanup launchers explicitly pass --apply, retaining their one-click behavior. ANALISAR_JELLYFIN.cmd runs only the audit.

All logs are metadata-only reports, never video backups. Cleanup deletions are permanent; move undo does not restore deleted files. No video copying or content hashes are used by the controller. Generate a fresh move preview after cleanup.

## Duplicate releases

Groups require matching normalized title, season and episode/range. Higher resolution wins; at equal resolution a known Erai-raws release wins over known other fansubs. Unknown/same-fansub ties remain in the review report. Local fansub_provenance.json can recover fansub labels from previous naming plans. Hardlink duplicates are detected by filesystem identity. Identical independent copies cannot be proven without reading their contents and are not automatically deleted solely for matching size. Movies are not deduplicated by guessed titles.

## Read-only audit

Lists image/NFO leftovers, empty folders, nested videos, nonstandard episode names, matching episode groups, zero-byte videos and companion files. Reads library paths and selected flags from Jellyfin options.xml plus error counts from the newest log. Server path defaults to C:\ProgramData\Jellyfin\Server and can be overridden using jellyfin_server in local settings. No database, media contents or secrets are read. Names needing review are not proof of broken media. The report is a snapshot; concurrent downloads or reorganization can change it.

For lighter scans, review chapter/trickplay extraction during library scanning. Disable local NFO saving if the media directories should stay free of NFO files. Embedded titles/episode information can override the intended file naming; review those options if release titles appear in the UI. Do not delete Jellyfin databases or its metadata directory as routine cleanup. Rescan after moving files. Pause torrents and Jellyfin scanning/image generation before organizing or deleting images to avoid concurrent file changes. MKA audio and subtitles are companions, not junk.

References: https://jellyfin.org/docs/general/server/media/shows/ and https://jellyfin.org/docs/general/server/media/movies/

## Image/NFO cleanup

Deletes only .nfo and image extensions, including JPG/JPEG/PNG/WebP/GIF/BMP/TIFF/AVIF/HEIC/ICO/SVG. Image files inside trickplay are included. Videos, subtitles, other file types and directories are excluded. Symlinks/junctions are skipped and each path is checked against the explicit roots. A report lists selected/deleted paths and failures.

Deletion is permanent and has no app undo. The cleanup report is a log, not a content backup. Let Jellyfin regenerate metadata and artwork if needed. Pause metadata/image generation if you need the folders to remain free of regenerated assets. No empty-directory cleanup is performed.

## Naming and catalog rules

Supports S01E02, dash episode numbers, ranges, v2, season suffixes, roman numerals II through VI, bracketed releases and Unicode. A deterministic filename-path label preserves multiple releases; it does not read video contents. Only exact-basename companions follow a video. NFO and shared artwork are left unchanged by organization itself; use cleanup to remove them.

Names cannot prove catalog episode ordering. Inferred seasons are marked in preview notes. Absolute numbering, named arcs, specials and ambiguous patterns can require explicit mappings. TMDB and TVDB may use different season orders.

Copy rules.example.json to local_rules.json. Folder rules support series, season, episode_offset, provider_id and folder (an existing direct anime folder). File rules take precedence and support series/season/episode/end_episode/provider_id/folder, or type=movie with title/year/provider_id. skip=true excludes an item. Use verified identifiers and special episode numbers.

## Checks and undo

Moves use file identity, size and modification time, not content hashes. Metadata checks cannot detect changes that preserve those attributes. Cross-filesystem moves are refused; there is no automatic copy fallback. Torrent paths change after moving.

Destinations are never overwritten. Journals record prepared/completed moves. Undo renames completed moves back and refuses changed identities or occupied source paths. Old copy/hardlink journals require matching originals for safe automated undo. Interrupted prepared records require manual inspection.

Manual reversal: use each completed journal entry to return the destination to its original path only if that path is free. Preserve originals before removing old linked/copied output. Keep move journals if you want to undo moves. Empty folders may remain. Cleanup deletions are separate from move journals and cannot be undone by option 3.

## Tests

    python -m unittest discover -s . -v

Tests cover existing-folder layout, rejection of nested/old destinations, movies routing, no-copy moves and undo, re-running previews, naming, conflicts, Unicode, metadata association, and cleanup preserving videos/subtitles. Hardlink integration may be skipped when host permissions deny it.
