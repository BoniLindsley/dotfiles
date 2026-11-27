#!/bin/sh
# Helper for an objectives record (objectives-record skill).
#
#   sh record.sh list           open entries, one line each
#   sh record.sh applies PATH   entries whose applies: covers PATH
#   sh record.sh next PREFIX    next free ID, such as T or AC
#   sh record.sh check          entries, logs or index not in the record's format
#   sh record.sh cite COMMIT    stable ID of a code commit, created if needed
#   sh record.sh commit ID      code commits a stable ID names
#   sh record.sh unrecorded     code commits newer than any the record cites
#
# Entries start with lines `---`, `id:`, `status:`, `summary:`,
# and for tasks `objective:` on line 5.
# Stable IDs are notes in refs/notes/stable-id, kept through rebases
# by notes.rewriteRef.
set -eu
if [ "${1:-}" = cite ]; then
    # Resolve before leaving the caller's directory, where HEAD is the code.
    target=$(git rev-parse --verify "${2:?commit}^{commit}")
fi
cd "$(dirname "$0")"
open='proposed|active|paused|long-term|todo|in_progress|blocked|awaiting_user|accepted|deferred|holds|unverified'
done='completed|cancelled|done|rejected|superseded|retired|failed'

list() {
    awk -v open="^($open)\$" '
    FNR == 2 { id = substr($0, 5) }
    FNR == 3 { status = substr($0, 9) }
    FNR == 4 { summary = substr($0, 10) }
    FNR == 5 && status ~ open {
        parent = /^objective: / ? substr($0, 12) : ""
        print index("OTDCA", substr(id, 1, 1)) " " parent " " id "\t- " id \
            " `[" status "]`" (parent == "" ? "" : " " parent ":") " " summary
    }' entries/*.md | sort | cut -f 2-
}

applies() {
    awk -v path="$1" '/^applies: / {
        n = split(substr($0, 10), word, /[ ,;()]+/)
        for (i = 1; i <= n; i++)
            if (word[i] == path || (word[i] ~ /\/$/ && index(path, word[i]) == 1)) {
                print substr(FILENAME, 9, length(FILENAME) - 11)
                break
            }
    }' entries/*.md
}

next_id() {
    last=$(grep -rohwE "$1-[0-9]+" entries log | sort -t- -k2 -n | tail -1)
    last=$(echo "${last:-0}" | sed 's/.*-0*//')
    printf '%s-%03d\n' "$1" $((${last:-0} + 1))
}

cite() {
    git config --get-all notes.rewriteRef | grep -qxF refs/notes/stable-id ||
        git config --add notes.rewriteRef refs/notes/stable-id
    id=$(git notes --ref=stable-id show "$1" 2>/dev/null |
        sed -n '/^commit_[k-z]\{16\}$/{p;q;}')
    if [ -z "$id" ]; then
        id=commit_$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n' | tr 0-9a-f k-z)
        git notes --ref=stable-id append -m "$id" "$1"
    fi
    echo "$id"
}

commit() {
    git log --exclude='meta/*' --branches --notes=stable-id -F --grep="$1" \
        --format='%h %s'
}

unrecorded() {
    branch=$(git symbolic-ref --short HEAD)
    branch=${branch#meta/}
    branch=${branch%/objectives}
    CITED=$(grep -rhoE 'commit_[k-z]{16}' entries log OBJECTIVES.md) || :
    export CITED
    notes=--no-notes
    git show-ref -q --verify refs/notes/stable-id && notes=--notes=stable-id
    git log "$notes" --format='C %h %s%n%N' "$branch" | awk '
    BEGIN { n = split(ENVIRON["CITED"], c, "\n"); for (i = 1; i <= n; i++) cited[c[i]] }
    /^C / { if (line != "") print line; line = substr($0, 3); next }
    $0 in cited { found = 1; exit }
    END { if (!found && line != "") print line }'
}

check() {
    {
        awk -v status="^status: ($open|$done)\$" '
        FNR == 1 && $0 != "---" ||
        FNR == 2 && $0 != "id: " substr(FILENAME, 9, length(FILENAME) - 11) ||
        FNR == 3 && $0 !~ status ||
        FNR == 4 && $0 !~ /^summary: ./ ||
        FNR == 5 && FILENAME ~ /\/T-/ && $0 !~ /^objective: O-[0-9]+$/ {
            print FILENAME ":" FNR ": " $0
        }' entries/*.md
        grep -h '^objective: ' entries/T-*.md | sort -u | while read -r _ id; do
            [ -f "entries/$id.md" ] || echo "entries: objective $id has no file"
        done
        grep -rnE '\b([A-Z]{1,2})-[0-9]{3} to [A-Z]{1,2}-[0-9]{3}\b' entries log OBJECTIVES.md \
            | sed 's/$/  (ID range)/'
        grep -nvE '^(- |# Log: |$)' log/*.md | sed 's/$/  (log line format)/'
        awk '/^## Status/ { on = 1 } /^## Artifacts/ { on = 0 }
        on { size += length($0) + 1 }
        END { if (size > 4000)
            print "OBJECTIVES.md: Status to Handoff has " size " characters, over 4000" }
        ' OBJECTIVES.md
        awk -v open="^($open)\$" '
        function flush(   rest, named, live) {
            rest = item
            while (match(rest, /(^|[^A-Z])[OTDCA]-[0-9]+/)) {
                id = substr(rest, RSTART, RLENGTH); sub(/^[^A-Z]/, "", id)
                named++; if (status[id] ~ open) live++
                rest = substr(rest, RSTART + RLENGTH)
            }
            if (named && !live) print "OBJECTIVES.md:" start ": " substr(item, 1, 60) "...  (Handoff item names only finished entries)"
            item = ""
        }
        FILENAME != "OBJECTIVES.md" {
            if (FNR == 2) id = substr($0, 5)
            if (FNR == 3) status[id] = substr($0, 9)
            next
        }
        /^#/ { if (item != "") flush(); on = /^### Handoff/; next }
        on && /^- / { if (item != "") flush(); item = $0; start = FNR; next }
        on && /^  / { item = item " " $0 }
        END { if (item != "") flush() }
        ' entries/*.md OBJECTIVES.md
        cited=$(grep -rnoE 'commit_[k-z]{16}' entries log OBJECTIVES.md) || :
        if [ -n "$cited" ] || git show-ref -q --verify refs/notes/stable-id; then
            git config --get-all notes.rewriteRef | grep -qxF refs/notes/stable-id ||
                echo "git: notes.rewriteRef lacks refs/notes/stable-id" \
                    "(sh record.sh cite sets it)"
            known=$(git log --exclude='meta/*' --branches --notes=stable-id \
                --format=%N 2>/dev/null) || :
            printf '%s\n' "$cited" | while IFS= read -r hit; do
                [ -n "$hit" ] || continue
                case "$known" in *"${hit##*:}"*) ;; *)
                    echo "$hit  (no commit on a code branch has this ID)" ;;
                esac
            done
        fi
    } || true
}

case "${1:-}" in
list) list ;;
applies) applies "${2:?path}" ;;
next) next_id "${2:?prefix}" ;;
cite) cite "$target" ;;
commit) commit "${2:?stable ID}" ;;
unrecorded) unrecorded ;;
check)
    problems=$(check)
    [ -z "$problems" ] && echo "No problems found." && exit 0
    printf '%s\n' "$problems"
    exit 1
    ;;
*)
    sed -n '2,13s/^# \{0,1\}//p' "${0##*/}" >&2
    exit 2
    ;;
esac
