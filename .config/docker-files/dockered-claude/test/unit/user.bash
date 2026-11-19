# Tests of the user configuration:
# reading it, and adding its mounts.
# test/run sources test/lib.bash first,
# which sets launcher and temporary_directory,
# and whose capture sets output, errors and status.
# shellcheck disable=SC2154

# shellcheck source=../../bin/dockered-claude
source -- "${launcher}" || return

# Declare, as globals of the test's subshell,
# the state that the launcher's run declares for the user configuration,
# with HOME and the working directory in temporary_directory,
# and check_mount_path, tested apart, allowing everything.
reset_user() {
  set_launcher_paths
  declare -gA kwargs=() mount_modes=() unsaved_mount_paths=()
  declare -gA mount_given_paths=() link_targets=() link_climbs=()
  declare -ga user_mounts=() user_persists=() mount_paths=() link_paths=()
  HOME="${temporary_directory}/home"
  user_config="${HOME}/.config/dockered-claude/config"
  workdir="${temporary_directory}/project"
  mkdir -p -- "${HOME}/.config/dockered-claude" "${workdir}"
  # shellcheck disable=SC2329 # Called by add_mount.
  check_mount_path() { :; }
}

# Write the arguments as lines of user_config.
write_user_config() {
  printf '%s\n' "$@" >"${user_config}"
}

test_reading_takes_mounts_and_persisted_paths_without_a_leading_tilde() {
  reset_user
  write_user_config '# Mine' '' 'mount = ~/notes:rw' 'mount = /srv/data' \
    'persists = ~/.bash_history' '  persists=notes/  '
  capture read_user_config
  assert_status 0
  assert_array user_mounts notes:rw /srv/data
  assert_array user_persists .bash_history notes/
}

test_reading_without_a_file_succeeds() {
  reset_user
  capture read_user_config
  assert_status 0
  assert_array user_mounts
}

test_reading_refuses_other_keys_and_invalid_values() {
  reset_user
  write_user_config 'profile = default'
  capture read_user_config
  assert_status 1
  assert_contains "${errors}" "${user_config}:1: unknown key 'profile'"
  write_user_config '' 'persists = ../escape'
  capture read_user_config
  assert_status 1
  assert_contains "${errors}" "${user_config}:2: invalid persisted path"
  write_user_config 'mount = a,b'
  capture read_user_config
  assert_status 1
  assert_contains "${errors}" "${user_config}:1: invalid mount"
}

test_user_mounts_are_relative_to_the_home_and_never_saved() {
  reset_user
  mkdir -p -- "${HOME}/notes" "${temporary_directory}/srv"
  user_mounts=(notes:rw "${temporary_directory}/srv" missing)
  capture add_user_mounts
  assert_status 0
  assert_array mount_paths "${HOME}/notes" "${temporary_directory}/srv"
  assert_equal rw "${mount_modes["${HOME}/notes"]}"
  assert_equal 2 "${#unsaved_mount_paths[@]}"
  assert_contains "${errors}" "skipping user mount '${HOME}/missing'"
}

test_user_mounts_keep_the_mode_of_a_mount_given_already() {
  reset_user
  mkdir -p -- "${HOME}/notes"
  mount_paths=("${HOME}/notes")
  mount_modes["${HOME}/notes"]=ro
  user_mounts=(notes:rw)
  capture add_user_mounts
  assert_status 0
  assert_array mount_paths "${HOME}/notes"
  assert_equal ro "${mount_modes["${HOME}/notes"]}"
  assert_equal 0 "${#unsaved_mount_paths[@]}"
}

test_a_refused_user_mount_names_the_configuration() {
  reset_user
  mkdir -p -- "${HOME}/notes"
  # shellcheck disable=SC2329 # Called by add_mount.
  check_mount_path() { return 1; }
  user_mounts=(notes)
  capture add_user_mounts
  assert_status 1
  assert_contains "${errors}" "${user_config}: cannot mount '${HOME}/notes'"
}
