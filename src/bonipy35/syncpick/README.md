# syncpick

Compare two rclone locations and copy picked files in either direction.
Pick files in a browser page,
or print a comparison from the command line.
Requires rclone on `PATH`, or `--rclone PATH`.

## Web page

Serve the page on localhost, optionally with both locations filled in:

```sh
python -m bonipy35.syncpick web remote:dir some/directory
```

Open the printed address, which includes this run's token;
requests without it are refused.
With both locations given, the page compares them when it opens.
The table hides files that are the same until their filter is ticked.
Tick files, then copy them left to right or right to left:
each button counts only the ticked files on its source side.
Each file's result shows as it finishes,
and the comparison refreshes afterwards.
Stop ends copying within a file or two.
Nothing is deleted.
Press Ctrl+C to stop the server.
`--port PORT` picks the port instead of any free one.

## Comparing

Print one tab-separated line per file:
state, left size and time, right size and time (UTC), then the path.

```sh
python -m bonipy35.syncpick compare remote:dir some/directory
```

States are those of `rclone check --combined`:
`=` same, `*` different, `+` left only, `-` right only, `!` error.
A missing side shows `-` for its size and time,
and a location that does not exist compares as empty.
The exit status is 0 if all files are the same,
1 if any differ, and 2 on errors.

## Trying the building blocks

Run rclone with any arguments, or print its version without any:

```sh
python -m bonipy35.syncpick runner
python -m bonipy35.syncpick runner lsjson -R --files-only some/directory
```

Start `rclone rcd` on localhost and send one request,
printing the JSON result:

```sh
python -m bonipy35.syncpick rc core/version
python -m bonipy35.syncpick rc operations/list \
  '{"fs": "some/directory", "remote": "", "opt": {"recurse": true}}'
```

Without a request, `rc` serves until Ctrl+C,
printing an `rclone rc` command with this run's credentials:

```sh
python -m bonipy35.syncpick rc
```

All commands accept `--config PATH` to use another rclone configuration file.
