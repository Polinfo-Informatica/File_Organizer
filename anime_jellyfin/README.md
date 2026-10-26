# Anime Jellyfin Organizer

Python 3.10+, standard library only. Open Run.cmd, or INICIAR.cmd in the customized package.

The default is now FAST MOVE: direct same-filesystem rename. It does not copy videos or read their contents to calculate hashes. Cross-filesystem moves are refused. Copy and hardlink modes require explicit CLI selection.

Without --target, the source root is also the destination root. Organized files go under Shows/Series/Season 01 and Movies/Title (Year). In-place scanning excludes these generated subtrees. Torrent paths change after moves.

Menu: 1 preview, 2 apply moves, 3 undo, 4 reports. Local settings and rules remain in local_settings.json and local_rules.json. Plans, journals and backups stay local.

CLI examples:

    python organize_anime.py plan --source "D:\Downloads\Anime" --output "logs\plan.json"
    python organize_anime.py apply --plan "logs\plan.json"
    python organize_anime.py undo --journal "logs\journal-ID.jsonl"

Naming supports S01E02, dash numbers, ranges, v2 revisions, season markers, roman suffixes, bracketed releases and Unicode. Filename-path identifiers preserve multiple versions; calculating them does not read video data. Exact matching subtitles, external audio and episode thumbnails follow the video. Original NFO, shared artwork and trickplay are left for Jellyfin to regenerate in the new library.

The review report lists special cases requiring explicit catalog mappings. Season assumptions also appear in preview notes. Correct filename syntax does not prove correct catalog order. Check the configured Jellyfin provider. Rules examples show folder-level season/offset mappings, per-file specials and movie mappings. Files and folders can be skipped explicitly. Provider IDs accept TMDB/TVDB/IMDb identifiers appropriate to the media.

Moves use quick file-identity, size and modification-time checks. These checks cannot detect content changes that preserve those attributes. Use stable completed downloads. Conflicting destinations stop apply; files are never overwritten. Existing hardlinks can be adopted. Existing independent copies require matching size/time and an earlier completed copy journal with the exact paths.

Journals record prepared and completed operations. Undo renames completed moves back, checks identity and refuses occupied original paths. Adopted existing destinations are preserved during undo. Old journals without identity information require matching originals for automated reversal; inspect uncertain legacy moves manually. Interrupted prepared entries are deliberately left for inspection.

Manual recovery: use the journal to return each completed destination to its original source path only when that path is free. Preserve originals before removing old copied/linked output. Keep journals. Empty folders may remain. Restore scripts from backups to revert the app version; media changes require journal undo or manual path restoration.

Tests: python -m unittest discover -s . -v
Tests cover parsing, mapping, conflicts, Unicode, copy/move/undo and in-place moving without invoking the copy routine. Optional hardlink integration is skipped when the host denies link creation.

Jellyfin libraries: add Shows as Shows and Movies as Movies. Do not also scan the original messy parent as the same library.
