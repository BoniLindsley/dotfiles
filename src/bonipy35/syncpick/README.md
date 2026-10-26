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
Files show as a tree, with each directory's counts by state.
Directories with only identical files start collapsed.
The state filters hide files, and directories with none left.
Tick files or whole directories,
then copy them left to right or right to left:
each button counts only the ticked files on its source side.
Each file's result shows as it finishes,
and the comparison refreshes afterwards.
Stop ends copying within a file or two.
Nothing is deleted.
Press Ctrl+C to stop the server.
`--port PORT` picks the port instead of any free one.

## Terminal

Compare and copy in the terminal, with the same tree as the web page:

```sh
python -m bonipy35.syncpick tui remote:dir some/directory
```

| Key | Action |
| --- | --- |
| Up, Down, `k`, `j`, PgUp, PgDn, Home, End | Move |
| Space | Pick or unpick a file or directory |
| Enter, Right | Expand a directory |
| Left | Collapse a directory, or go to its parent |
| `>`, `<` | Copy picked files to the right, or to the left |
| `=` | Show or hide identical files |
| `r` | Compare again |
| Esc | Stop copying after the current file |
| `q` | Quit |

Times are in UTC to the minute.
On Windows it needs `windows-curses`, and does not work yet.

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
