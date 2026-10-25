# syncpick

Compare two rclone locations and copy picked files in either direction.
Work in progress: comparing works from the command line;
copying exists as a library function for the coming frontends.
Requires rclone on `PATH`, or `--rclone PATH`.

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

Both accept `--config PATH` to use another rclone configuration file.
