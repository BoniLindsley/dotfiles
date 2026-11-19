# Tests of resolving, checking and selecting mounts.
# test/run sources test/lib.bash first,
# which sets launcher and temporary_directory,
# and whose capture sets output, errors and status.
# shellcheck disable=SC2154

# shellcheck source=../../bin/dockered-claude
source -- "${launcher}" || return

# Declare, as globals of the test's subshell,
# the state that the launcher's run declares for mounts,
# with a working directory that holds the project
# and need not exist.
reset_mounts() {
  set_launcher_paths
  declare -gA kwargs=() mount_modes=()
  declare -ga mounts=() project_mounts=() mount_paths=()
  home=/home/someone
  workdir=/home/someone/project
  project_root="${workdir}"
  project_config="${project_root}/${project_config_path}"
}

# Declare the state for select_mounts,
# with the working directory in temporary_directory,
# which is under /tmp, a path that cannot be mounted;
# check_mount_path is tested apart, so it allows everything here.
reset_selection() {
  reset_mounts
  workdir="${temporary_directory}/project"
  project_root="${workdir}"
  project_config="${project_root}/${project_config_path}"
  mkdir -p -- "${workdir}"
  # shellcheck disable=SC2329 # Called by select_mounts.
  check_mount_path() { :; }
}

test_resolving_makes_a_relative_path_absolute() {
  reset_mounts
  resolve_mount_spec library/../notes:rw /base
  assert_equal /base/notes "${mount_path}"
  assert_equal rw "${mount_mode}"
}

test_resolving_defaults_to_read_only() {
  reset_mounts
  resolve_mount_spec /srv/data /base
  assert_equal /srv/data "${mount_path}"
  assert_equal ro "${mount_mode}"
}

test_resolving_follows_symbolic_links() {
  reset_mounts
  mkdir -- "${temporary_directory}/target"
  ln -s -- target "${temporary_directory}/link"
  resolve_mount_spec link "${temporary_directory}"
  assert_equal "${temporary_directory}/target" "${mount_path}"
}

test_checking_refuses_a_system_directory() {
  reset_mounts
  capture check_mount_path /usr/share
  assert_status 1
  assert_contains "${errors}" 'it would replace /usr'
}

test_checking_refuses_a_parent_of_a_system_directory() {
  reset_mounts
  capture check_mount_path /opt
  assert_status 1
  assert_contains "${errors}" 'it would hide /opt/tools'
}

test_checking_refuses_claude_state() {
  reset_mounts
  capture check_mount_path /home/someone/.claude/projects
  assert_status 1
  assert_contains "${errors}" 'it would replace /home/someone/.claude'
}

test_checking_refuses_what_the_launcher_mounts() {
  reset_mounts
  capture check_mount_path /home/someone/.agents/skills
  assert_status 1
  assert_contains "${errors}" 'it would replace /home/someone/.agents'
}

test_checking_allows_a_parent_of_what_the_launcher_mounts() {
  reset_mounts
  capture check_mount_path /home/someone/.config
  assert_status 0
}

test_checking_refuses_the_working_directory() {
  reset_mounts
  capture check_mount_path "${workdir}"
  assert_status 1
  assert_contains "${errors}" 'it is the working directory'
}

test_checking_refuses_the_launcher_configuration() {
  reset_mounts
  capture check_mount_path "${project_config%/*}"
  assert_status 1
  assert_contains "${errors}" "it holds the launcher's configuration"
}

test_checking_allows_another_directory() {
  reset_mounts
  capture check_mount_path /home/someone/src/library
  assert_status 0
  assert_equal '' "${errors}"
}

test_adding_a_path_again_keeps_its_place_and_takes_the_new_mode() {
  reset_mounts
  for spec in /srv/a /srv/b /srv/a:rw; do
    split_mount_spec "${spec}"
    add_mount
  done
  assert_array mount_paths /srv/a /srv/b
  assert_equal rw "${mount_modes["/srv/a"]}"
  assert_equal ro "${mount_modes["/srv/b"]}"
}

test_selecting_skips_a_saved_mount_that_is_missing() {
  reset_selection
  mkdir -- "${temporary_directory}/present"
  project_mounts=(../present ../missing:rw)
  capture select_mounts
  assert_status 0
  assert_array mount_paths "${temporary_directory}/present"
  assert_contains "${errors}" \
    "skipping saved mount '${temporary_directory}/missing'"
}

test_selecting_fails_for_a_given_mount_that_is_missing() {
  reset_selection
  kwargs[mounts_given]=1
  mounts=(../missing)
  capture select_mounts
  assert_status 1
  assert_contains "${errors}" \
    "cannot mount '${temporary_directory}/missing': it does not exist"
}

test_selecting_given_mounts_ignores_saved_ones() {
  reset_selection
  mkdir -- "${temporary_directory}/given" "${temporary_directory}/saved"
  kwargs[mounts_given]=1
  mounts=(../given:rw)
  project_mounts=(../saved)
  capture select_mounts
  assert_status 0
  assert_array mount_paths "${temporary_directory}/given"
  assert_equal rw "${mount_modes["${temporary_directory}/given"]}"
}
