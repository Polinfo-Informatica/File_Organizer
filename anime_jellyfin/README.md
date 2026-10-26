# Anime Jellyfin Organizer

Windows-oriented Python 3.10+ organizer using only the standard library. It builds a separate Jellyfin library from torrent downloads without renaming the source videos. Planning is read-only; applying is a separate command.

## Quick start

Double-click `Run.cmd`. The first run asks for source and destination directories. Option 1 creates a preview; option 2 deliberately applies it; option 3 undoes the last journal. Local settings, plans and inventory are excluded from Git.

Or use the CLI:

```powershell
python organize_anime.py plan --source "D:\Downloads\Anime" --target "D:\Media\Anime" --output "logs\plan.json"
python organize_anime.py apply --plan "logs\plan.json" --mode hardlink
python organize_anime.py undo --journal "logs\journal-ID.jsonl"
```

Use a new plan filename for each run. The tool never overwrites an existing plan, journal or destination file. Add `--rules local_rules.json` to the planning command when using custom rules.

## Jellyfin setup

Add the output `Shows` directory as a **Shows** library and the output `Movies` directory as a **Movies** library. Do not add the output parent, and do not simultaneously include the original downloads in the same library.

TV episodes use `Shows/Series/Season 02/Series - S02E03 - 1080p [release-id].mkv`. Movie rules use `Movies/Title (Year)/Title (Year).mkv`. Each release receives a deterministic label so different resolutions, fansubs, encodes and revisions are preserved as versions instead of overwriting each other.

Supported candidates include SubsPlease/Erai dash numbering, `S01E02`, `S01E01-E02`, `01-02`, `01v2`, `S3`, `Season 2`, `2nd Season`, roman season suffixes II through VI, season subfolders, bracket-only release titles such as `[Group][Series][08][1080p]`, Unicode titles, and loose videos at the source root.

**A valid filename does not establish catalog identity or catalog episode order.** Seasons inferred from title suffixes and default season 1 are explicitly marked in the preview. Check these against the metadata provider configured in Jellyfin. For example, TMDB and TVDB can arrange the same anime into different seasons. The tool does not silently choose a catalog or claim to have verified every match online.

Absolute numbering above 50 without a season marker, ambiguous numbered sequels, named arcs, episode zero, fractional episodes, OVAs, specials, movies without explicit rules, and unknown patterns go to the review report. They remain untouched. An absolute episode below 51 may still be in a later season: review the inferred-order notes, not only the review report.

## Special cases and catalog mappings

Copy `rules.example.json` to `local_rules.json` and replace the examples with real mappings. Folder keys are exact top-level source directory names. File keys are exact forward-slash paths relative to the source root. File rules take precedence; `skip: true` excludes a file/folder.

Folder rules can set `series`, `season`, `episode_offset`, and optional `provider_id`. An offset converts continuous numbering to season-relative numbering. A folder mapping with a season explicitly permits parsing an otherwise ambiguous arc/sequel title. Use file rules when one source folder mixes seasons, specials or movies. Provider IDs use `tmdbid-123`, `tvdbid-123` or `imdbid-tt123`; movie rules support TMDB or IMDb. Use actual IDs, not the example numbers. Keep the mapping consistent with the installed Jellyfin providers and selected episode order.

TV file rules require `series`, `season`, `episode`, and optionally `end_episode` and `provider_id`. `season: 0` is for a special whose catalog number you have verified. Movie file rules require `type: movie` and `title`, with optional `year` and `provider_id`. Movies are never automatically assigned a TV episode number.

## Existing Jellyfin files

The inventory distinguishes videos, subtitles/audio companions, NFO metadata, artwork, trickplay and other files. Only exact-basename subtitle/audio companions and `-thumb.jpg`/`-thumb.png` thumbnails follow a video. Language and forced/default flags are preserved. Embedded tracks remain intact because the media is never transcoded.

Original `.nfo` files, shared series artwork, databases, shortcuts and `.trickplay` directories stay in the source. NFO files may contain episode numbers/IDs from earlier incorrect matches; copying them could override the corrected filenames. Old trickplay is not copied under a guessed name. Jellyfin regenerates metadata, shared images and trickplay in the new library. Existing `tvshow.nfo` titles/IDs are recorded as evidence for review, not blindly trusted as mappings. No artwork or metadata is deleted.

## Operations and recovery

- `hardlink` (default): preserves torrent paths and avoids duplicate video storage on the same filesystem, normally NTFS on Windows. Companions are copied. If hardlink creation is unavailable, the operation stops; it never silently switches to a space-consuming copy. Editing either hardlink edits the same video data. Removing one link preserves the other.
- `copy`: preserves originals but needs enough disk space for full copies.
- `move`: copies with exclusive creation, verifies SHA-256, then removes the source. This breaks existing torrent paths and is an explicit opt-in. It is slower and needs temporary free space even on the same volume.

Process only completed, stable downloads. The tool checks size/time snapshots and SHA-256 during apply. It cannot prove torrent completeness from a filename; pause active transfers and Jellyfin scanning while applying. Hash verification reads whole videos and can take time.

Every operation is journaled before execution and after completion, with source, destination and SHA-256. Undo processes completed operations in reverse order, refuses changed files and occupied restore paths, and records each reversal. For copy/hardlink undo, the original must still exist and match. Keep journals until satisfied. Empty directories are preserved.

After a power loss or interruption, inspect any `prepared` record without a matching `completed` record. Such an entry may have created a complete or partial destination; automated undo deliberately leaves it for manual inspection. Compare source/destination SHA-256 before manually removing a partial copy or restoring a moved source. Do not blindly rerun apply over partial output.

Manual reversal: for hardlink/copy, verify that original files are intact, then remove only the destinations listed in the journal. For move, return each completed destination to its recorded source after checking its hash and ensuring the source path is free. Revert Jellyfin's library directory setting to the original source if you changed it. Keep the original directories and metadata until the new library is verified.

Symlinks/junctions are excluded, and destinations outside the configured root are rejected. Collision protection is checked across the entire batch before media changes. Existing destinations stop apply; this version does not incrementally reconcile a previous completed import.

## Validation

```powershell
python -m unittest discover -s . -v
```

Tests exercise parsing, ranges, versions, metadata separation, thumbnail matching, mappings, movie routing, overwrite prevention, source changes, Unicode, boundary checks, copy/move and undo. The hardlink integration check reports a skip when the host denies link creation; it must be verified on the destination Windows filesystem.

References: [Jellyfin TV naming](https://jellyfin.org/docs/general/server/media/shows/), [movies](https://jellyfin.org/docs/general/server/media/movies/), [provider identifiers](https://jellyfin.org/docs/general/server/metadata/identifiers/).
