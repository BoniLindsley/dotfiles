---
name: bash-style
description: >
  Describes personal preferred Bash style
  for writing, modifying and reviewing shell scripts:
  script layout with __help, warn, parse_arguments, run and main,
  sourcing-safe scaffolding, error handling with || return,
  declare, quoting and braces.
metadata:
  version: 1.0.0
---

When given file paths,
review or rewrite them to conform to this guide.
Flag deviations that conflict with existing codebase conventions
rather than silently overriding them.

# Script Structure and Order

- `#!/usr/bin/env bash`, with no `set` options at the top.
- `__help`: prints usage, a summary, options and environment variables
  from a heredoc, using `${script_name}`.
  Do not print help by stripping comments with `sed`.
- `warn`: prints `script_name: message` to standard error.
- `parse_arguments`: fills `kwargs` and `args`,
  warning and returning 1 on bad usage.
- Helper functions, each preceded by a comment
  when its purpose or a decision in it is not obvious.
  Constants that only some functions use
  may be declared at the top level just above them.
- A `run` function doing the work from explicit parameters,
  as an entry point for other scripts and tests that source this one.
- A `main` function that declares the shared state,
  parses arguments, handles `--help`,
  resolves defaults, and calls `run`.
- Scaffolding that sets shell options and calls `main`
  only when the script is executed, not sourced.

Example:

```bash
#!/usr/bin/env bash

__help() {
  cat <<HELP
Usage: ${script_name} [--help] [--force] NAME

Greet NAME.

  -h, --help              Show this help
  -f, --force             Greet even when NAME was greeted already

Environment:
  GREETING                Greeting to use (default: Hello)
HELP
}

warn() {
  printf '%s: %s\n' "${script_name}" "$*" >&2
}

parse_arguments() {
  declare argument
  while (($#)); do
    argument="$1"
    shift
    case "${argument}" in
    -h | --help) kwargs[help]=1 ;;
    -f | --force) kwargs[force]=1 ;;
    --)
      args+=("$@")
      break
      ;;
    -?*)
      warn "unknown option '${argument}'"
      return 1
      ;;
    *) args+=("${argument}") ;;
    esac
  done
}

# Greet NAME with GREETING.
run() {
  declare name="$1" greeting="$2"
  printf '%s, %s!\n' "${greeting}" "${name}"
}

main() {
  declare script_name
  script_name="$(basename -- "${BASH_SOURCE[0]}")" || return

  declare -A kwargs=()
  declare -a args=()

  parse_arguments "$@" || return
  if [[ -n "${kwargs[help]+defined}" ]]; then
    __help
    return
  fi
  if ((${#args[@]} != 1)); then
    warn "expected one NAME"
    return 1
  fi

  run "${args[0]}" "${GREETING:-Hello}" || return
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  set -euo pipefail
  main "$@"
fi
```

# Arguments

- `kwargs` is an associative array of options:
  `1` for flags, the value for options taking one.
  Test a flag with `[[ -n "${kwargs[name]+defined}" ]]`.
- `args` is an array of the remaining arguments.
  After `--`, or wherever the script passes the rest through
  to another command, append them all and stop parsing.
- Options that collect repeated values,
  such as `--tool NAME`, append to their own array,
  declared in `main`.
- Validate values in `parse_arguments`
  with a `validate_*` function that warns and returns 1,
  so that bad usage fails before any work starts.

# State and Scope

- Use `declare` rather than `local`, inside functions;
  it is local there, and the same keyword as at the top level.
- `main` declares the state shared between functions,
  such as resolved paths, `kwargs` and `args`.
  The functions it calls read and set them through dynamic scope,
  without globals leaking into a shell that sources the script.
- A function that sets a variable for its caller,
  instead of printing a result,
  says so in its comment, as in "Set drafts_dir to …".
- Give `run` its inputs as parameters,
  so that it does not depend on how `main` found them.

# Errors

- `set -euo pipefail` is set only in the scaffolding.
  Sourcing the script for tests leaves the caller's options alone.
- Errexit does not apply inside a function called from `||` or `if`,
  which is how `main` calls them,
  so follow every command that can fail with `|| return`,
  including command substitutions in assignments:
  `name="$(basename -- "${path}")" || return`.
  Assign a substitution separately from `declare`,
  whose own status would hide it.
- Report errors with `warn`, then `return 1`.
  Do not `exit` inside functions;
  `main` returns and the scaffolding exits with its status.
- Clean up temporary files on the failure path
  before returning.
- Write files to a temporary file beside them
  and `mv` it over the target,
  so that an interrupted run cannot leave half a file.

# Syntax

- Indent with 2 spaces, as `shfmt -i 2` formats,
  with `case` patterns at the level of `case`.
- Quote and brace every expansion: `"${name}"`, `"${array[@]}"`,
  except inside `(( ))` and array subscripts.
- Use `[[ ]]` for tests and `(( ))` for arithmetic;
  use `declare -i` for counters.
- Put `--` before operands of commands that accept it,
  such as `mkdir -p -- "${directory}"` and `rm -f -- "${file}"`.
- Use `printf` rather than `echo`.
- Prefer parameter expansion to external commands when equally clear,
  such as `"${path##*/}"` for a base name in a loop.
- Wrap long command lines with a trailing `\` or after `|`, `&&` or `||`,
  and list many arguments one per line in an array:

  ```bash
  docker_args+=(
    --init
    --read-only
    --rm
  )
  ```
