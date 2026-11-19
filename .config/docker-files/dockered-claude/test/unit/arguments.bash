# Tests of the launcher's argument parsing.
# test/run sources test/lib.bash first,
# which sets launcher and temporary_directory,
# and whose capture sets output, errors and status.
# shellcheck disable=SC2154

# shellcheck source=../../bin/dockered-claude
source -- "${launcher}" || return

# Declare, as globals of the test's subshell,
# the arrays that the launcher's main declares for parse_arguments.
reset_arguments() {
  set_launcher_paths
  declare -gA kwargs=()
  declare -ga args=() tools=() packages=() mounts=()
}

test_tools_accumulate_in_order() {
  reset_arguments
  capture parse_arguments --tool rclone -t uv
  assert_status 0
  assert_array tools rclone uv
  assert_equal 1 "${kwargs[tools_given]}"
}

test_no_tools_clears_the_tools_before_it() {
  reset_arguments
  capture parse_arguments --tool rclone --no-tools --tool uv
  assert_status 0
  assert_array tools uv
}

test_first_unknown_argument_starts_claude_arguments() {
  reset_arguments
  capture parse_arguments --tool uv -p 'fix it' --tool rclone
  assert_status 0
  assert_array tools uv
  assert_array args -p 'fix it' --tool rclone
}

test_double_dash_passes_the_rest_to_claude() {
  reset_arguments
  capture parse_arguments -- --help
  assert_status 0
  assert_array args --help
  assert_equal '' "${kwargs[help]:-}"
}

test_tool_requires_a_name() {
  reset_arguments
  capture parse_arguments --tool
  assert_status 1
  assert_contains "${errors}" '--tool requires a tool name'
}

test_invalid_tool_name_is_refused() {
  reset_arguments
  capture parse_arguments --tool ../escape
  assert_status 1
  assert_contains "${errors}" "invalid tool name '../escape'"
}

test_packages_accumulate() {
  reset_arguments
  capture parse_arguments --package libssl-dev --package g++
  assert_status 0
  assert_array packages libssl-dev g++
  assert_equal 1 "${kwargs[packages_given]}"
}

test_invalid_package_name_is_refused() {
  reset_arguments
  capture parse_arguments --package 'gcc;rm'
  assert_status 1
  assert_contains "${errors}" "invalid package name 'gcc;rm'"
}

test_mounts_keep_their_mode_suffix() {
  reset_arguments
  capture parse_arguments --mount ~/notes:rw -m ../library
  assert_status 0
  assert_array mounts ~/notes:rw ../library
}

test_mount_with_a_comma_is_refused() {
  reset_arguments
  capture parse_arguments --mount 'a,b'
  assert_status 1
  assert_contains "${errors}" "invalid mount 'a,b'"
}

test_no_mounts_clears_the_mounts_before_it() {
  reset_arguments
  capture parse_arguments --mount /srv --no-mounts
  assert_status 0
  assert_array mounts
  assert_equal 1 "${kwargs[mounts_given]}"
}

test_flags_are_set() {
  reset_arguments
  capture parse_arguments --no-save -h
  assert_status 0
  assert_equal '1 1' "${kwargs[no_save]} ${kwargs[help]}"
}

test_no_arguments_run_claude() {
  reset_arguments
  capture parse_arguments
  assert_status 0
  assert_equal run "${kwargs[command]}"
  assert_array args
}

test_an_option_first_runs_claude() {
  reset_arguments
  capture parse_arguments --tool uv -p 'fix it'
  assert_status 0
  assert_equal run "${kwargs[command]}"
  assert_array tools uv
  assert_array args -p 'fix it'
}

test_run_passes_a_prompt_to_claude() {
  reset_arguments
  capture parse_arguments run --no-save 'fix the tests'
  assert_status 0
  assert_equal run "${kwargs[command]}"
  assert_equal 1 "${kwargs[no_save]}"
  assert_array args 'fix the tests'
}

test_run_passes_a_word_naming_a_command_to_claude() {
  reset_arguments
  capture parse_arguments run build
  assert_status 0
  assert_equal run "${kwargs[command]}"
  assert_array args build
}

test_a_word_that_is_not_a_command_is_refused() {
  reset_arguments
  capture parse_arguments 'fix the tests'
  assert_status 1
  assert_contains "${errors}" "unknown command 'fix the tests'"
  assert_contains "${errors}" 'run'
}

test_options_that_became_commands_are_refused() {
  declare option
  for option in -b --build --build-tool --list-tools; do
    reset_arguments
    capture parse_arguments "${option}"
    assert_status 1
    assert_contains "${errors}" "${option} was replaced by"
  done
}

test_build_takes_no_arguments() {
  reset_arguments
  capture parse_arguments build
  assert_status 0
  assert_equal build "${kwargs[command]}"

  reset_arguments
  capture parse_arguments build --tool uv
  assert_status 1
  assert_contains "${errors}" "unexpected argument '--tool'"
}

test_tool_list() {
  reset_arguments
  capture parse_arguments tool list
  assert_status 0
  assert_equal tool-list "${kwargs[command]}"
}

test_tool_build_takes_names() {
  reset_arguments
  capture parse_arguments tool build vcpkg uv
  assert_status 0
  assert_equal tool-build "${kwargs[command]}"
  assert_array args vcpkg uv
  assert_array tools
}

test_tool_build_requires_a_name() {
  reset_arguments
  capture parse_arguments tool build
  assert_status 1
  assert_contains "${errors}" 'tool build requires a tool name'
}

test_tool_build_refuses_an_invalid_name() {
  reset_arguments
  capture parse_arguments tool build uv ../escape
  assert_status 1
  assert_contains "${errors}" "invalid tool name '../escape'"
}

test_tool_requires_a_known_subcommand() {
  reset_arguments
  capture parse_arguments tool
  assert_status 1
  assert_contains "${errors}" 'tool requires list or build'

  reset_arguments
  capture parse_arguments tool remove uv
  assert_status 1
  assert_contains "${errors}" "unknown tool command 'remove'"
}

test_help_is_accepted_after_a_command() {
  declare command
  for command in run build profile tool clean; do
    reset_arguments
    capture parse_arguments "${command}" --help
    assert_status 0
    assert_equal 1 "${kwargs[help]}"
  done
}

test_profile_is_set() {
  reset_arguments
  capture parse_arguments --profile minimal
  assert_status 0
  assert_equal minimal "${kwargs[profile]}"
}

test_profile_requires_a_name() {
  reset_arguments
  capture parse_arguments --profile
  assert_status 1
  assert_contains "${errors}" '--profile requires a profile name'
}

test_invalid_profile_name_is_refused() {
  reset_arguments
  capture parse_arguments --profile Default
  assert_status 1
  assert_contains "${errors}" "invalid profile name 'Default'"
}

test_profile_list() {
  reset_arguments
  capture parse_arguments profile list
  assert_status 0
  assert_equal profile-list "${kwargs[command]}"
}

test_profile_build_takes_names() {
  reset_arguments
  capture parse_arguments profile build default minimal
  assert_status 0
  assert_equal profile-build "${kwargs[command]}"
  assert_array args default minimal
}

test_profile_build_requires_a_valid_name() {
  reset_arguments
  capture parse_arguments profile build
  assert_status 1
  assert_contains "${errors}" 'profile build requires a profile name'

  reset_arguments
  capture parse_arguments profile build ../escape
  assert_status 1
  assert_contains "${errors}" "invalid profile name '../escape'"
}

test_tool_commands_take_a_profile() {
  reset_arguments
  capture parse_arguments tool list --profile minimal
  assert_status 0
  assert_equal minimal "${kwargs[profile]}"

  reset_arguments
  capture parse_arguments tool build uv --profile minimal vcpkg
  assert_status 0
  assert_equal minimal "${kwargs[profile]}"
  assert_array args uv vcpkg
}

test_tool_list_takes_no_names() {
  reset_arguments
  capture parse_arguments tool list uv
  assert_status 1
  assert_contains "${errors}" "tool list: unexpected argument 'uv'"
}

test_profile_commands_take_no_profile() {
  reset_arguments
  capture parse_arguments profile build --profile minimal default
  assert_status 1
  assert_contains "${errors}" "profile build: unexpected argument '--profile'"
}

test_clean_takes_targets_and_dry_run() {
  reset_arguments
  capture parse_arguments clean tools --list packages
  assert_status 0
  assert_equal clean "${kwargs[command]}"
  assert_equal 1 "${kwargs[dry_run]}"
  assert_array args tools packages
}

test_clean_takes_all() {
  reset_arguments
  capture parse_arguments clean --dry-run all
  assert_status 0
  assert_array args all
}

test_clean_requires_a_target() {
  reset_arguments
  capture parse_arguments clean --dry-run
  assert_status 1
  assert_contains "${errors}" \
    'clean requires a target: containers tools packages profiles or all'
}

test_clean_refuses_an_unknown_target() {
  reset_arguments
  capture parse_arguments clean volumes
  assert_status 1
  assert_contains "${errors}" "unknown clean target 'volumes'"
}

test_clean_refuses_an_unknown_option() {
  reset_arguments
  capture parse_arguments clean --force all
  assert_status 1
  assert_contains "${errors}" "clean: unexpected argument '--force'"
}
