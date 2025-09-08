BEFORE

Finished loading records into memory in 1517.08s, now running the ORM inserts.
Found 2,615,660 duplicate submissions.
Found 341,491 submissions with invalid dates.
Found 69,696 submissions with missing data.
Dropped 393,189 tracks with no artist.
Tracks with year=0: 163350 / 1921455
Inserted artists and albums in 11.32 seconds
Inserted 1921455 records in 1187.81 seconds
Inserted M2M pairings for TrackArtist and AlbumArtist in 1002.40 seconds
Exported feature matrix and indexes in 55.27 seconds

AFTER
Finished loading records into memory in 1334.82s, now running the ORM inserts.
Found 2,615,660 duplicate submissions.
Found 341,491 submissions with invalid dates.
Found 69,696 submissions with missing data.
Dropped 393,189 tracks with no artist.
Tracks with year=0: 163350 / 1921455
Inserted artists and albums in 8.26 seconds
Inserted 1921455 records in 336.06 seconds
Inserted M2M pairings for TrackArtist and AlbumArtist in 450.99 seconds
Exported feature matrix and indexes in 25.06 seconds


Optimization consisted of:
- Increasing batch size for `bulk_create` from 2K to 20K
- Wrap DB inserts in `transaction.atomic()`
- Set `synchronous_commit` off