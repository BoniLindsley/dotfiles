# Open entries of an objectives record, one line each.
# Usage: awk -f list.awk entries/*.md | sort | cut -f 2-
FNR == 1 { id = st = ob = su = ""; head = ($0 == "---"); next }
head && $0 == "---" {
    if (st ~ /^(proposed|active|paused|long-term|todo|in_progress|blocked|awaiting_user|accepted|deferred|holds|unverified)$/)
        print index("OTDCA", substr(id, 1, 1)) " " ob " " id "\t- " id " `[" st "]`" (ob == "" ? "" : " " ob ":") " " su
    head = 0
}
head {
    key = $0; sub(/:.*/, "", key)
    val = $0; sub(/^[^:]*: */, "", val)
    if (key == "id") id = val
    else if (key == "status") st = val
    else if (key == "objective") ob = val
    else if (key == "summary") su = val
}
