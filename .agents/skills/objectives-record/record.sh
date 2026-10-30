#!/bin/sh
# Helper for an objectives record (objectives-record skill).
# Run from anywhere; it works in the directory holding this script.
#
#   sh record.sh list           open entries, one line each
#   sh record.sh update         rewrite `Open entries` in OBJECTIVES.md
#   sh record.sh check          check the invariants; exit 1 on problems
#   sh record.sh applies PATH   entries whose applies: covers PATH
#   sh record.sh next PREFIX    next free ID, such as T or AC
set -eu
cd "$(dirname "$0")"

# Prints "id<TAB>status<TAB>objective<TAB>summary<TAB>applies" per entry.
headers() {
    awk '
    FNR == 1 { id = st = ob = su = ap = ""; head = ($0 == "---"); next }
    head && $0 == "---" { print id "\t" st "\t" ob "\t" su "\t" ap; head = 0 }
    head {
        key = $0; sub(/:.*/, "", key)
        val = $0; sub(/^[^:]*: */, "", val)
        if (key == "id") id = val
        else if (key == "status") st = val
        else if (key == "objective") ob = val
        else if (key == "summary") su = val
        else if (key == "applies") ap = val
    }' entries/*.md
}

list() {
    headers | awk -F '\t' '
    $2 ~ /^(proposed|active|paused|long-term|todo|in_progress|blocked|awaiting_user|accepted|deferred|holds|unverified)$/ {
        print index("OTDCA", substr($1, 1, 1)) " " $3 " " $1 "\t- " $1 " `[" $2 "]`" ($3 == "" ? "" : " " $3 ":") " " $4
    }' | sort | cut -f 2-
}

update() {
    list > OBJECTIVES.md.list
    awk '
    FNR == NR { items = items $0 "\n"; next }
    /^## Open entries$/ { print; print ""; printf "%s", items; skip = 1; next }
    skip && /^## / { print ""; skip = 0 }
    !skip { print }
    ' OBJECTIVES.md.list OBJECTIVES.md > OBJECTIVES.md.new
    rm OBJECTIVES.md.list
    mv OBJECTIVES.md.new OBJECTIVES.md
}

applies() {
    headers | awk -F '\t' -v path="$1" '
    {
        n = split($5, word, /[ ,;()]+/)
        for (i = 1; i <= n; i++)
            if (word[i] == path || (word[i] ~ /\/$/ && index(path, word[i]) == 1)) {
                print $1 " `[" $2 "]` " $4
                break
            }
    }'
}

next_id() {
    last=$(grep -rohwE "$1-[0-9]+" entries log 2>/dev/null \
        | sort -t- -k2 -n | tail -1 | sed 's/.*-0*//')
    printf '%s-%03d\n' "$1" $((${last:-0} + 1))
}

check() {
    problems=$(
        awk '
        function fail(msg) { print file ": " msg }
        FNR == 1 {
            if (NR > 1) finish()
            file = FILENAME
            split("", h); head = ($0 == "---"); body = ""; next
        }
        head && $0 == "---" { head = 0; next }
        head {
            key = $0; sub(/:.*/, "", key)
            val = $0; sub(/^[^:]*: */, "", val)
            h[key] = val; next
        }
        { body = body $0 "\n" }
        function finish(   f, t, ok, n, i, d) {
            f = file; sub(/.*\//, "", f); sub(/\.md$/, "", f)
            t = substr(f, 1, 1)
            if (h["id"] != f) fail("id is " h["id"])
            ok = "O proposed active paused long-term completed cancelled|T todo in_progress blocked done cancelled|D proposed awaiting_user accepted rejected deferred superseded|C active retired|A unverified holds failed retired"
            if (index(ok, t " ") == 0 || !match(ok, t " [a-z_ -]*")) fail("unknown type")
            else if (index(" " substr(ok, RSTART + 2, RLENGTH - 2) " ", " " h["status"] " ") == 0) fail("status " h["status"])
            if (t ~ /[ODCA]/ && h["applies"] == "") fail("no applies")
            if (t == "O" && h["status"] == "active" && body !~ /\n- AC-[0-9]+:/) fail("active objective without criteria")
            if (t == "T") { task[f] = h["objective"]; deps[f] = h["depends"] }
            if (t == "O") tasks[f] = body
            if ((h["status"] == "done" || h["status"] == "completed") && body !~ /## (Evidence|Delivered)/) fail("no evidence")
            if (h["status"] == "blocked" && h["depends"] == "") fail("blocked without depends")
            if (h["status"] == "deferred" && h["revisit"] == "") fail("deferred without revisit")
            if (h["status"] == "superseded" && h["superseded_by"] == "") fail("superseded without superseded_by")
            if (h["status"] == "awaiting_user" && (h["asked"] == "" || body !~ /## Question/)) fail("awaiting_user without asked or question")
            seen[f] = 1
            n = split(body, line, "\n")
            for (i = 1; i <= n; i++) if (match(line[i], /^- AC-[0-9]+:/)) {
                d = substr(line[i], 3, RLENGTH - 3)
                if (d in ac) fail(d " also defined in " ac[d]); else ac[d] = f
            }
        }
        END {
            finish()
            for (f in task) {
                if (!(task[f] in seen)) print "entries/" f ".md: objective " task[f] " missing"
                else if (index(tasks[task[f]], "\n- " f ":") == 0 && index(tasks[task[f]], "- " f ":") != 1)
                    print "entries/" f ".md: not listed in " task[f]
                n = split(deps[f], d, /, */)
                for (i = 1; i <= n; i++)
                    if (d[i] ~ /^[OTDCA]-[0-9]+$/ && !(d[i] in seen)) print "entries/" f ".md: depends on missing " d[i]
            }
        }' entries/*.md
        grep -rnE '\b([A-Z]{1,2})-[0-9]{3} to [A-Z]{1,2}-[0-9]{3}\b' entries log OBJECTIVES.md \
            | sed 's/$/  (ID range)/' || true
        for id in $(grep -rohwE '(O|T|D|C|A)-[0-9]{3}' entries | sort -u); do
            [ -f "entries/$id.md" ] || echo "entries: $id referenced but has no file"
        done
        if [ -d data ]; then
            for dir in data/*/; do
                id=$(basename "$dir")
                [ -f "entries/$id.md" ] || { echo "$dir: no entry $id"; continue; }
                for file in "$dir"*; do
                    grep -qF "$(basename "$file")" "entries/$id.md" \
                        || echo "$file: not named in entries/$id.md"
                done
            done
        fi
        list > OBJECTIVES.md.list
        awk '/^## Open entries$/ { on = 1; next } on && /^## / { on = 0 } on && /^- / { print }' \
            OBJECTIVES.md | diff OBJECTIVES.md.list - > /dev/null \
            || echo "OBJECTIVES.md: Open entries differ from the list; run: sh record.sh update"
        rm -f OBJECTIVES.md.list
    )
    if [ -n "$problems" ]; then
        printf '%s\n' "$problems"
        return 1
    fi
    echo "No problems found."
}

case "${1:-}" in
list) list ;;
update) update ;;
check) check ;;
applies) applies "${2:?path}" ;;
next) next_id "${2:?prefix}" ;;
*)
    sed -n '2,9s/^# \{0,1\}//p' "$0" >&2
    exit 2
    ;;
esac
