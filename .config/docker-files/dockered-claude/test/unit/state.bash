# Tests of where Claude Code's state is kept, and of migrating it
# from where earlier versions kept it.
# test/run sources test/lib.bash first,
# which sets launcher and temporary_directory,
# and whose capture sets output, errors and status.
# shellcheck disable=SC2154

# shellcheck source=../../bin/dockered-claude
source -- "${launcher}" || return

# Set the state paths in temporary_directory, none of them created,
# with a fake docker listing fake_running as running containers.
reset_state() {
  set_launcher_paths
  state_dir="${temporary_directory}/state"
  state_home="${state_dir}/home/claude"
  claude_state="${state_dir}/tools/claude-code/.claude"
  persists_home="${state_dir}/persists/home/claude"
  fake_running=''
  # shellcheck disable=SC2329 # Called by migrate_state.
  docker() {
    [[ "$1" == ps ]] || return 1
    printf '%s' "${fake_running}"
  }
}

# Make the state of an earlier version:
# .claude with a file in it, and .claude.json.
make_old_state() {
  mkdir -p -- "${state_home}/.claude"
  printf 'history\n' >"${state_home}/.claude/history.jsonl"
  printf '{}\n' >"${state_home}/.claude.json"
}

test_migrating_moves_the_directory_then_the_configuration_into_it() {
  reset_state
  make_old_state
  capture migrate_state
  assert_status 0
  assert_file "${claude_state}/history.jsonl" history
  assert_file "${claude_state}/.claude.json" '{}'
  [[ ! -e "${state_home}" && ! -e "${state_dir}/home" ]] ||
    fail "expected the old home to be gone"
  [[ -d "${persists_home}" ]] || fail "expected the old home in persists"
  assert_equal "${script_name}: moved ${state_home}/.claude to ${claude_state}
${script_name}: moved ${state_home}/.claude.json to ${claude_state}/.claude.json
${script_name}: moved ${state_home} to ${persists_home}" \
    "${errors}"
}

test_migrating_moves_the_rest_of_the_home_to_persists() {
  reset_state
  # Claude Code's state was migrated already,
  # and a run made an empty .claude as a mount point since.
  mkdir -p -- "${claude_state}" "${state_home}/.claude" "${state_home}/.npm" \
    "${state_dir}/home/other"
  printf 'ls\n' >"${state_home}/.bash_history"
  capture migrate_state
  assert_status 0
  assert_file "${persists_home}/.bash_history" ls
  [[ -d "${persists_home}/.npm" && ! -e "${persists_home}/.claude" ]] ||
    fail "expected .npm kept and the empty .claude dropped"
  [[ -d "${state_dir}/home/other" ]] || fail "expected other homes kept"
  assert_equal "${script_name}: moved ${state_home} to ${persists_home}" \
    "${errors}"
}

test_migrating_the_home_never_overwrites_persists() {
  reset_state
  mkdir -p -- "${state_home}" "${persists_home}"
  capture migrate_state
  assert_status 1
  assert_equal "${script_name}: cannot move ${state_home}: ${persists_home} exists" \
    "${errors}"
  [[ -d "${state_home}" ]] || fail "expected the old home kept"
}

test_migrating_is_refused_while_a_container_runs() {
  reset_state
  make_old_state
  fake_running=$'quirky_name\nother_name\n'
  capture migrate_state
  assert_status 1
  assert_equal "${script_name}: cannot migrate while containers of the launcher run: quirky_name, other_name; end them first" \
    "${errors}"
  [[ -e "${state_home}/.claude/history.jsonl" && ! -e "${claude_state}" ]] ||
    fail "expected nothing to be moved"
}

test_migrating_never_overwrites() {
  reset_state
  make_old_state
  mkdir -p -- "${claude_state}"
  printf '{"new": 1}\n' >"${claude_state}/.claude.json"
  rm -r -- "${state_home}/.claude"
  capture migrate_state
  assert_status 1
  assert_equal "${script_name}: cannot move ${state_home}/.claude.json: ${claude_state}/.claude.json exists" \
    "${errors}"
  assert_file "${claude_state}/.claude.json" '{"new": 1}'
}

test_migrating_without_old_state_says_so() {
  reset_state
  mkdir -p -- "${state_dir}"
  capture migrate_state
  assert_status 0
  assert_equal "${script_name}: nothing to migrate" "${errors}"
}

test_a_run_with_unmigrated_state_fails_naming_the_command() {
  reset_state
  make_old_state
  capture check_migrated_state
  assert_status 1
  assert_equal "${script_name}: Claude Code's state from an earlier version is in ${state_home}/.claude and ${state_home}/.claude.json; move it with: ${script_name} migrate" \
    "${errors}"
}

test_a_run_after_migrating_or_without_state_goes_ahead() {
  reset_state
  capture check_migrated_state
  assert_status 0
  mkdir -p -- "${claude_state}" "${persists_home}"
  capture check_migrated_state
  assert_status 0
}

test_a_run_with_the_old_home_fails_naming_the_command() {
  reset_state
  # An earlier run made .claude as an empty mount point.
  mkdir -p -- "${state_home}/.claude" "${claude_state}"
  capture check_migrated_state
  assert_status 1
  assert_equal "${script_name}: the home of an earlier version is in ${state_home}; move it with: ${script_name} migrate" \
    "${errors}"
}

test_preparing_the_state_makes_it_private_to_the_user() {
  reset_state
  capture prepare_state_directory
  assert_status 0
  [[ -d "${claude_state}/skills" ]] || fail "expected the state directories"
  [[ ! -e "${state_dir}/home" ]] || fail "expected no home in the state"
  assert_equal 700 "$(stat -c %a -- "${claude_state}")"
  assert_equal 700 "$(stat -c %a -- "${state_dir}/tools")"
}

test_the_command_line_takes_migrate() {
  declare -gA kwargs=()
  declare -ga args=()
  set_launcher_paths
  capture parse_arguments migrate
  assert_status 0
  assert_equal migrate "${kwargs[command]}"
  capture parse_arguments migrate now
  assert_status 1
  assert_equal "${script_name}: migrate: unexpected argument 'now'" "${errors}"
}
