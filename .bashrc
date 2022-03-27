# .bashrc: executed by bash for non-login shells.
# Loaded whenever a shell is started without logging in.
# E.g. Running scripts, new virtual terminal.

source_executables_in_dir() {
  local dir_path
  local path
  for dir_path in "$@"; do
    for path in ${dir_path}/*; do
      # Only source executable scripts.
      if [[ -x "${path}" ]]; then
        source "${path}"
      fi
    done
  done
}

source_executables_in_dir \
  "${XDG_CONFIG_HOME-"${HOME-.}/.config"}/bash/rc.d"
