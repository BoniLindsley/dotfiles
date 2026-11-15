#!/usr/bin/env bash

__help() {
  cat <<HELP
Usage: ${script_name} [--help] [--all] [DRAFTS_DIR]

Install skill drafts from a project's .meta/drafts/skills
over the installed skills in ~/.agents/skills.

First choose drafts to see their diffs,
then go on to choose drafts to install.

  -h, --help              Show this help
  -a, --all               Install every draft that differs, without prompting

DRAFTS_DIR defaults to .meta/drafts/skills
in the nearest directory up from the working directory holding .meta,
else in the root of the git repository, else in the working directory.

Environment:
  AGENTS_SKILLS_DIR       Installed skills directory
                          (default: \$HOME/.agents/skills)
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
    -a | --all) kwargs[all]=1 ;;
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
  if ((${#args[@]} > 1)); then
    warn "expected at most one drafts directory, got ${#args[@]}"
    return 1
  fi
}

# Set drafts_dir to .meta/drafts/skills in the nearest directory up
# from the working directory holding .meta,
# since projects outside git keep one too;
# failing that, in the root of the git repository or the working directory.
find_drafts_directory() {
  declare root="${PWD}"
  while [[ ! -d "${root}/.meta" && "${root}" != / ]]; do
    root="$(dirname -- "${root}")" || return
  done
  if [[ ! -d "${root}/.meta" ]]; then
    root="$(git rev-parse --show-toplevel 2>/dev/null)" || root="${PWD}"
  fi
  drafts_dir="${root%/}/.meta/drafts/skills"
}

# Print the version in a SKILL.md front matter, or nothing.
version_of() {
  declare file="$1"
  [[ -f "${file}" ]] || return 0
  awk 'NR == 1 && $0 == "---" { inside = 1; next }
       inside && $0 == "---" { exit }
       inside && $1 == "version:" { print $2; exit }' "${file}"
}

# Print the names of drafts that differ from the installed skill.
changed_skills() {
  declare draft name
  for draft in "${drafts_dir}"/*/; do
    [[ -f "${draft}SKILL.md" ]] || continue
    draft="${draft%/}"
    name="${draft##*/}"
    if ! diff -rq -- "${draft}" "${skills_dir}/${name}" >/dev/null 2>&1; then
      printf '%s\n' "${name}"
    fi
  done
}

# Print how many installed files the draft would remove.
removed_count() {
  declare name="$1" file
  declare -i count=0
  while IFS= read -r -d '' file; do
    [[ -e "${drafts_dir}/${name}/${file}" ]] || count+=1
  done < <(cd -- "${skills_dir}/${name}" && find . -type f -print0)
  printf '%d' "${count}"
}

label_of() {
  declare name="$1" old new removed
  if [[ ! -e "${skills_dir}/${name}" ]]; then
    printf '%s (new)' "${name}"
    return 0
  fi
  old="$(version_of "${skills_dir}/${name}/SKILL.md")" || return
  new="$(version_of "${drafts_dir}/${name}/SKILL.md")" || return
  printf '%s (%s -> %s' "${name}" "${old:-unversioned}" "${new:-unversioned}"
  removed="$(removed_count "${name}")" || return
  if ((removed == 1)); then
    printf ', removes 1 file'
  elif ((removed > 1)); then
    printf ', removes %d files' "${removed}"
  fi
  printf ')'
}

install_skill() {
  declare name="$1" target parent staging old
  target="${skills_dir}/${name}"
  # Replace the directory a link points to, keeping the link.
  if [[ -L "${target}" ]]; then
    target="$(realpath -- "${target}")" || return
  fi
  parent="$(dirname -- "${target}")" || return
  mkdir -p -- "${parent}" || return

  # Copy beside the target and swap,
  # so that a failed copy never leaves a half-written skill.
  staging="$(mktemp -d -- "${parent}/.${name}.new.XXXXXX")" || return
  if ! cp -a -- "${drafts_dir}/${name}/." "${staging}/" ||
    ! chmod --reference="${drafts_dir}/${name}" -- "${staging}"; then
    rm -rf -- "${staging}"
    return 1
  fi
  if [[ -e "${target}" ]]; then
    old="$(mktemp -u -- "${parent}/.${name}.old.XXXXXX")" || return
    mv -- "${target}" "${old}" || return
    mv -- "${staging}" "${target}" || return
    rm -rf -- "${old}" || return
  else
    mv -- "${staging}" "${target}" || return
  fi
  printf 'Installed %s.\n' "${name}"
}

show_diff() {
  declare name="$1" installed empty=''
  installed="${skills_dir}/${name}"
  # Compare a new skill with an empty directory, showing all its files.
  if [[ ! -e "${installed}" ]]; then
    empty="$(mktemp -d)" || return
    installed="${empty}"
  fi
  # diff exits with 1 when the files differ, and 2 on trouble.
  declare -i status=0
  diff -ruN --color=auto -- "${installed}" "${drafts_dir}/${name}" ||
    status=$?
  if [[ -n "${empty}" ]]; then
    rmdir -- "${empty}" || return
  fi
  ((status < 2))
}

# Set names to the drafts that differ, saying so when none do.
load_names() {
  mapfile -t names < <(changed_skills) || return
  if ((${#names[@]} == 0)); then
    printf 'No drafts in %s differ from %s.\n' "${drafts_dir}" "${skills_dir}"
  fi
}

# Offer FIRST, then each draft in names, prompting with PROMPT.
# Set choice to "first", a skill name,
# or nothing on q or at end of input.
choose() {
  declare first="$1" PS3="$2" label name
  declare -a labels=("${first}")
  for name in "${names[@]}"; do
    label="$(label_of "${name}")" || return
    labels+=("${label}")
  done

  printf '\nDrafts that differ from %s:\n' "${skills_dir}"
  choice=''
  select label in "${labels[@]}"; do
    if [[ "${REPLY}" == q ]]; then
      return 0
    elif [[ -n "${label}" ]]; then
      if ((REPLY == 1)); then
        choice=first
      else
        choice="${names[REPLY - 2]}"
      fi
      return 0
    fi
    printf 'No such option: %s\n' "${REPLY}"
  done
  # select fails at end of input, which means quit.
  return 0
}

install_names() {
  declare name
  for name in "${names[@]}"; do
    install_skill "${name}" || return
  done
}

# Review the diffs of the drafts,
# then install the chosen ones.
review_and_install() {
  declare choice

  while :; do
    load_names || return
    ((${#names[@]} > 0)) || return 0
    choose "Go on to install" "Show which diff? (number, q to quit): " ||
      return
    case "${choice}" in
    '') return 0 ;;
    first) break ;;
    *) show_diff "${choice}" || return ;;
    esac
  done

  while :; do
    load_names || return
    ((${#names[@]} > 0)) || return 0
    choose "All of the below" "Install which? (number, q to quit): " ||
      return
    case "${choice}" in
    '') return 0 ;;
    first) install_names || return ;;
    *) install_skill "${choice}" || return ;;
    esac
  done
}

# Install the drafts in args[0], or else found by find_drafts_directory,
# over the skills in AGENTS_SKILLS_DIR:
# all of those that differ with kwargs[all],
# else those chosen after reviewing their diffs.
run() {
  declare drafts_dir skills_dir
  declare -a names=()

  if ((${#args[@]} > 0)); then
    drafts_dir="${args[0]}"
  else
    find_drafts_directory || return
  fi
  skills_dir="${AGENTS_SKILLS_DIR:-${HOME:?}/.agents/skills}"

  if [[ ! -d "${drafts_dir}" ]]; then
    warn "no drafts directory: ${drafts_dir}"
    return 1
  fi

  if [[ -n "${kwargs[all]+defined}" ]]; then
    load_names || return
    install_names || return
    return 0
  fi
  review_and_install || return
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

  run || return
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  set -euo pipefail
  main "$@"
fi
