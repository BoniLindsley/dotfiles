# Tests of choosing a profile and naming its images.
# test/run sources test/lib.bash first,
# which sets launcher and temporary_directory,
# and whose capture sets output, errors and status.
# shellcheck disable=SC2154

# shellcheck source=../../bin/dockered-claude
source -- "${launcher}" || return

# Declare, as globals of the test's subshell,
# the state that select_profile reads,
# with the profiles default and minimal in a launcher directory
# in temporary_directory, and DOCKERED_CLAUDE_PROFILE unset.
reset_profiles() {
  set_launcher_paths
  declare -gA kwargs=() project_options=()
  project_directory="${temporary_directory}/launcher"
  mkdir -p -- "${project_directory}"/profiles/{default,minimal}
  : >"${project_directory}/profiles/default/Dockerfile"
  : >"${project_directory}/profiles/minimal/Dockerfile"
  unset DOCKERED_CLAUDE_PROFILE
}

test_selecting_defaults_to_the_default_profile() {
  reset_profiles
  capture select_profile
  assert_status 0
  assert_equal default "${profile}"
  assert_equal dockered-claude-default:latest "${image}"
  assert_equal "${image}" "${container_image}"
}

test_selecting_takes_the_environment_over_the_default() {
  reset_profiles
  DOCKERED_CLAUDE_PROFILE=minimal
  capture select_profile
  assert_status 0
  assert_equal dockered-claude-minimal:latest "${image}"
}

test_selecting_takes_the_configuration_over_the_environment() {
  reset_profiles
  DOCKERED_CLAUDE_PROFILE=default
  project_options[profile]=minimal
  capture select_profile
  assert_status 0
  assert_equal minimal "${profile}"
}

test_selecting_takes_the_option_over_the_configuration() {
  reset_profiles
  project_options[profile]=default
  kwargs[profile]=minimal
  capture select_profile
  assert_status 0
  assert_equal minimal "${profile}"
}

test_selecting_refuses_a_profile_without_a_dockerfile() {
  reset_profiles
  kwargs[profile]=missing
  capture select_profile
  assert_status 1
  assert_contains "${errors}" "no profile 'missing'"
}

test_selecting_refuses_an_invalid_name_from_the_environment() {
  reset_profiles
  DOCKERED_CLAUDE_PROFILE=../default
  capture select_profile
  assert_status 1
  assert_contains "${errors}" "invalid profile name '../default'"
}

# Declare, as globals of the test's subshell,
# the state that read_profile_launcher reads and sets,
# for the profile default with the launcher.bash given as the argument,
# run from a working directory in temporary_directory.
reset_launcher() {
  reset_profiles
  declare -gA mount_modes=() profile_mount_paths=()
  declare -ga mount_paths=() profile_variables=() profile_path_entries=()
  set_profile default
  home=/home/claude
  workdir="${temporary_directory}/work"
  project_root="${temporary_directory}/project"
  project_config="${project_root}/${project_config_path}"
  mkdir -p -- "${workdir}"
  cd -- "${workdir}" || return
  printf '%s\n' "$1" >"${project_directory}/profiles/default/launcher.bash"
}

# Allow every mount: temporary_directory is under /tmp,
# a path that cannot be mounted,
# and check_mount_path is tested apart.
allow_all_mounts() {
  # shellcheck disable=SC2329 # Called by add_mount.
  check_mount_path() { :; }
}

test_launcher_passes_variables_mounts_and_path_entries() {
  # shellcheck disable=SC2016 # Expanded by launcher.bash.
  reset_launcher '
profile_environment() {
  printf "%s\n" SET_VARIABLE "" UNSET_VARIABLE
}
profile_mounts() {
  printf "%s\n" data "${PWD%/*}/notes:rw" "${PWD}/missing"
}
profile_path() {
  printf "%s\n" /opt/sdk/bin /usr/local/go/bin
}'
  mkdir -p -- "${workdir}/data" "${temporary_directory}/notes"
  allow_all_mounts
  export SET_VARIABLE=1
  unset UNSET_VARIABLE
  capture read_profile_launcher
  assert_status 0
  assert_array profile_variables SET_VARIABLE
  assert_array mount_paths "${workdir}/data" "${temporary_directory}/notes"
  assert_equal ro "${mount_modes["${workdir}/data"]}"
  assert_equal rw "${mount_modes["${temporary_directory}/notes"]}"
  assert_equal 2 "${#profile_mount_paths[@]}"
  assert_contains "${errors}" "skipping profile mount '${workdir}/missing'"
  assert_array profile_path_entries /opt/sdk/bin /usr/local/go/bin
}

test_launcher_without_functions_adds_nothing() {
  reset_launcher '# Nothing to add.'
  capture read_profile_launcher
  assert_status 0
  assert_array profile_variables
  assert_array mount_paths
  assert_array profile_path_entries
}

test_profile_without_launcher_adds_nothing() {
  reset_launcher ''
  rm -- "${project_directory}/profiles/default/launcher.bash"
  capture read_profile_launcher
  assert_status 0
  assert_array profile_path_entries
}

test_launcher_with_an_error_stops_the_launch() {
  reset_launcher 'undefined_command'
  capture read_profile_launcher
  assert_status 1
  assert_contains "${errors}" 'launcher.bash: profile_environment failed'
}

test_launcher_function_with_an_error_inside_stops_the_launch() {
  reset_launcher '
profile_path() {
  false
  printf "%s\n" /opt/sdk/bin
}'
  capture read_profile_launcher
  assert_status 1
  assert_contains "${errors}" 'launcher.bash: profile_path failed'
  assert_array profile_path_entries
}

test_launcher_cannot_read_standard_input() {
  reset_launcher '
profile_path() {
  read -r line || printf "%s\n" /no/input
}'
  capture read_profile_launcher <<<'/from/input'
  assert_status 0
  assert_array profile_path_entries /no/input
}

test_launcher_cannot_pass_path() {
  reset_launcher 'profile_environment() { printf "%s\n" PATH; }'
  capture read_profile_launcher
  assert_status 1
  assert_contains "${errors}" "profile_environment: cannot pass 'PATH'"
}

test_launcher_cannot_pass_an_invalid_name() {
  reset_launcher 'profile_environment() { printf "%s\n" "A=B"; }'
  capture read_profile_launcher
  assert_status 1
  assert_contains "${errors}" "profile_environment: cannot pass 'A=B'"
}

test_launcher_path_entries_must_be_absolute() {
  reset_launcher 'profile_path() { printf "%s\n" bin; }'
  capture read_profile_launcher
  assert_status 1
  assert_contains "${errors}" "profile_path: invalid entry 'bin'"
}

test_launcher_mounts_go_through_the_mount_checks() {
  reset_launcher 'profile_mounts() { printf "%s\n" /usr/lib; }'
  capture read_profile_launcher
  assert_status 1
  assert_contains "${errors}" "cannot mount '/usr/lib'"
  assert_contains "${errors}" "profile_mounts: cannot mount '/usr/lib'"
}

test_launcher_mount_given_already_keeps_its_mode_and_is_saved() {
  reset_launcher 'profile_mounts() { printf "%s\n" data:rw; }'
  mkdir -p -- "${workdir}/data"
  mount_paths=("${workdir}/data")
  mount_modes["${workdir}/data"]=ro
  capture read_profile_launcher
  assert_status 0
  assert_array mount_paths "${workdir}/data"
  assert_equal ro "${mount_modes["${workdir}/data"]}"
  assert_equal 0 "${#profile_mount_paths[@]}"
}

test_saving_mounts_leaves_out_those_of_the_profile() {
  reset_launcher 'profile_mounts() { printf "%s\n" data; }'
  mkdir -p -- "${workdir}/data" "${workdir}/mine"
  allow_all_mounts
  declare -gA project_options=()
  mount_paths=("${workdir}/mine")
  mount_modes["${workdir}/mine"]=ro
  capture read_profile_launcher
  assert_status 0
  capture save_project_mounts
  assert_status 0
  assert_contains "$(<"${project_config}")" "mount = ${workdir}/mine"
  [[ "$(<"${project_config}")" != *"${workdir}/data"* ]] ||
    fail "expected the profile's mount not to be saved"
}
