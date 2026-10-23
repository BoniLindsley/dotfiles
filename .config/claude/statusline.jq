def window($name; $fmt):
  if . == null then empty
  else "\($name): \(.used_percentage | round)%"
    + (if .resets_at then
         " (resets \(.resets_at
           | if type == "number" then . else sub("\\.[0-9]+"; "") | fromdateiso8601 end
           | strflocaltime($fmt)))"
       else "" end)
  end;

(.context_window.current_usage // {}) as $u
| ([$u.input_tokens, $u.cache_creation_input_tokens, $u.cache_read_input_tokens]
   | map(. // 0) | add) as $in
| [ (.model.display_name // "unknown"),
    "in: \($in) tokens",
    (.rate_limits.five_hour | window("5h"; "%H:%M")),
    (.rate_limits.seven_day | window("7d"; "%a %H:%M")) ]
| join(" | ")
