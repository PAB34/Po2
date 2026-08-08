# Tennis data attribution

The files in `tml_wta/` are derived from the Jeff Sackmann tennis archive,
retrieved through the `Aneeshers/tennis-sackmann-archive` mirror on Hugging Face.
They are used for non-commercial statistical calibration and H2H context.

- Original work: Jeff Sackmann tennis data
- Mirror: https://huggingface.co/datasets/Aneeshers/tennis-sackmann-archive
- License: CC BY-NC-SA 4.0

The historical files in `tml/` come from the TennisMyLife database:
https://github.com/Tennismylife/TML-Database

TennisMyLife now keeps that GitHub repository for historical/technical reference
and publishes the live ATP database on:
https://stats.tennismylife.org/tennis-match-database

In production, PRONO retrieves only the current-year ATP CSV from
`https://stats.tennismylife.org/data/{year}.csv`. It is cached for 24 hours in
the private runtime volume, validated before use, and is not committed or
redistributed. If the live source is unavailable, the last valid runtime cache
is used, then the packaged historical file as a final fallback.

All TennisMyLife data is used only for this private, non-commercial dashboard.
