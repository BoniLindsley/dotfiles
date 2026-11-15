#!/usr/bin/env bash
# Install skill drafts from a project's .meta/drafts/skills
# over the installed skills in ~/.agents/skills.
#
# Usage: apply-skill-drafts [DRAFTS_DIR]
#
# DRAFTS_DIR defaults to .meta/drafts/skills
# in the nearest directory up from the working directory holding .meta.
# AGENTS_SKILLS_DIR overrides the installed skills directory.

set -euo pipefail

if [[ ${1-} == -h || ${1-} == --help ]]; then
    sed -n '2,9s/^# \{0,1\}//p' "$0"
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

while :; do
    mapfile -t names < <(changed_skills)
    if ((${#names[@]} == 0)); then
        echo "No drafts in $drafts_dir differ from $skills_dir."
        exit 0
    fi

    all="All of the below"
    labels=("$all")
    for name in "${names[@]}"; do
        labels+=("$(label_of "$name")")
    done

    echo
    echo "Drafts that differ from $skills_dir:"
    PS3="Install which? (number, q to quit): "
    chosen=""
    select choice in "${labels[@]}"; do
        if [[ $REPLY == q ]]; then
            exit 0
        elif [[ $choice == "$all" ]]; then
            chosen=all
            break
        elif [[ -n $choice ]]; then
            # Option 1 is "all", so skill options start at 2.
            chosen="${names[REPLY - 2]}"
            break
        fi
        echo "No such option: $REPLY"
    done
    # select ends without a choice at end of input.
    [[ -n $chosen ]] || exit 0

    if [[ $chosen == all ]]; then
        for name in "${names[@]}"; do
            install_skill "$name"
        done
    else
        install_skill "$chosen"
    fi
done
