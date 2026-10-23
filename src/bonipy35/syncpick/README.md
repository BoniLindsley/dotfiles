# syncpick

Compare two rclone locations and copy picked files in either direction.
Work in progress: only the rclone building blocks exist so far.
Requires rclone on `PATH`, or `--rclone PATH`.

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
