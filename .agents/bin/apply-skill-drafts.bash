#!/usr/bin/env bash
# Install skill drafts from a project's .meta/drafts/skills
# over the installed skills in ~/.agents/skills.
#
# Usage: apply-skill-drafts [DRAFTS_DIR]
#
# DRAFTS_DIR defaults to .meta/drafts/skills
# in the nearest directory up from the working directory holding .meta.
# AGENTS_SKILLS_DIR overrides the installed skills directory.
#
# First choose drafts to see their diffs,
# then go on to choose drafts to install.

set -euo pipefail

if [[ ${1-} == -h || ${1-} == --help ]]; then
    sed -n '2,12s/^# \{0,1\}//p' "$0"
    exit 0
fi

# The nearest directory up from here holding .meta,
# since projects outside git keep one too.
root="$PWD"
while [[ ! -d $root/.meta && $root != / ]]; do
    root="$(dirname "$root")"
done
[[ -d $root/.meta ]] || root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
drafts_dir="${1:-${root%/}/.meta/drafts/skills}"
skills_dir="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"

if [[ ! -d $drafts_dir ]]; then
    echo "No drafts directory: $drafts_dir" >&2
    exit 1
fi

# Prints the version in a SKILL.md front matter, or nothing.
version_of() {
    [[ -f $1 ]] || return 0
    awk 'NR == 1 && $0 == "---" { inside = 1; next }
         inside && $0 == "---" { exit }
         inside && $1 == "version:" { print $2; exit }' "$1"
}

# Prints the names of drafts that differ from the installed skill.
changed_skills() {
    local draft name
    for draft in "$drafts_dir"/*/; do
        [[ -f $draft/SKILL.md ]] || continue
        name="$(basename "$draft")"
        if ! diff -rq "$draft" "$skills_dir/$name" >/dev/null 2>&1; then
            printf '%s\n' "$name"
        fi
    done
}

# Prints how many installed files the draft would remove.
removed_count() {
    local name="$1" file count=0
    while IFS= read -r -d '' file; do
        [[ -e $drafts_dir/$name/$file ]] || ((++count))
    done < <(cd "$skills_dir/$name" && find . -type f -print0)
    printf '%d' "$count"
}

label_of() {
    local name="$1" old new removed
    if [[ ! -e $skills_dir/$name ]]; then
        printf '%s (new)' "$name"
        return
    fi
    old="$(version_of "$skills_dir/$name/SKILL.md")"
    new="$(version_of "$drafts_dir/$name/SKILL.md")"
    printf '%s (%s -> %s' "$name" "${old:-unversioned}" "${new:-unversioned}"
    removed="$(removed_count "$name")"
    if ((removed == 1)); then
        printf ', removes 1 file'
    elif ((removed > 1)); then
        printf ', removes %d files' "$removed"
    fi
    printf ')'
}

install_skill() {
    local name="$1" target parent staging old
    target="$skills_dir/$name"
    # Replace the directory a link points to, keeping the link.
    if [[ -L $target ]]; then
        target="$(realpath "$target")"
    fi
    parent="$(dirname "$target")"
    mkdir -p "$parent"

    # Copy beside the target and swap,
    # so that a failed copy never leaves a half-written skill.
    staging="$(mktemp -d "$parent/.$name.new.XXXXXX")"
    cp -a "$drafts_dir/$name/." "$staging/"
    chmod --reference="$drafts_dir/$name" "$staging"
    if [[ -e $target ]]; then
        old="$(mktemp -u "$parent/.$name.old.XXXXXX")"
        mv "$target" "$old"
        mv "$staging" "$target"
        rm -rf "$old"
    else
        mv "$staging" "$target"
    fi
    echo "Installed $name."
}

show_diff() {
    local name="$1" installed empty=""
    installed="$skills_dir/$name"
    # Compare a new skill with an empty directory, showing all its files.
    if [[ ! -e $installed ]]; then
        empty="$(mktemp -d)"
        installed="$empty"
    fi
    diff -ruN --color=auto "$installed" "$drafts_dir/$name" || true
    if [[ -n $empty ]]; then
        rmdir "$empty"
    fi
}

# Sets names to the drafts that differ, or exits when none do.
load_names() {
    mapfile -t names < <(changed_skills)
    if ((${#names[@]} == 0)); then
        echo "No drafts in $drafts_dir differ from $skills_dir."
        exit 0
    fi
}

# Offers FIRST, then each draft in names, prompting with PROMPT.
# Sets choice to "first", a skill name,
# or nothing on q or at end of input.
choose() {
    local first="$1" prompt="$2" label name labels
    labels=("$first")
    for name in "${names[@]}"; do
        labels+=("$(label_of "$name")")
    done

    echo
    echo "Drafts that differ from $skills_dir:"
    PS3="$prompt"
    choice=""
    select label in "${labels[@]}"; do
        if [[ $REPLY == q ]]; then
            return
        elif [[ -n $label ]]; then
            if ((REPLY == 1)); then
                choice=first
            else
                choice="${names[REPLY - 2]}"
            fi
            return
        fi
        echo "No such option: $REPLY"
    done
}

# Stage 1: review diffs.
while :; do
    load_names
    choose "Go on to install" "Show which diff? (number, q to quit): "
    case $choice in
        "") exit 0 ;;
        first) break ;;
        *) show_diff "$choice" ;;
    esac
done

# Stage 2: install.
while :; do
    load_names
    choose "All of the below" "Install which? (number, q to quit): "
    case $choice in
        "") exit 0 ;;
        first)
            for name in "${names[@]}"; do
                install_skill "$name"
            done
            ;;
        *) install_skill "$choice" ;;
    esac
done
