#!/bin/sh
# Helper for an objectives record (objectives-record skill).
#
#   sh record.sh list           open entries, one line each
#   sh record.sh applies PATH   entries whose applies: covers PATH
#   sh record.sh next PREFIX    next free ID, such as T or AC
#   sh record.sh check          entries, logs or index not in the record's format
#
# Entries start with lines `---`, `id:`, `status:`, `summary:`,
# and for tasks `objective:` on line 5.
set -eu
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
    } || true
}

case "${1:-}" in
list) list ;;
applies) applies "${2:?path}" ;;
next) next_id "${2:?prefix}" ;;
check)
    problems=$(check)
    [ -z "$problems" ] && echo "No problems found." && exit 0
    printf '%s\n' "$problems"
    exit 1
    ;;
*)
    sed -n '2,10s/^# \{0,1\}//p' "$0" >&2
    exit 2
    ;;
esac
