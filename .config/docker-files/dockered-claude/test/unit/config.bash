# Tests of finding, reading and saving the project configuration.
# test/run sources test/lib.bash first,
# which sets launcher and temporary_directory,
# and whose capture sets output, errors and status.
# shellcheck disable=SC2154

# shellcheck source=../../bin/dockered-claude
source -- "${launcher}" || return

# Declare, as globals of the test's subshell,
# the state that the launcher's run declares for the configuration,
# with project_root a new directory and project_config in it.
reset_configuration() {
  set_launcher_paths
  declare -gA kwargs=() project_options=() mount_modes=() unsaved_mount_paths=()
  declare -gA mount_given_paths=() link_targets=() link_climbs=()
  declare -ga project_mounts=() mount_paths=() link_paths=()
  project_root="${temporary_directory}/project"
  project_config="${project_root}/${project_config_path}"
  mkdir -p -- "${project_root}"
}

# Write the remaining arguments as lines of project_config.
write_config() {
  mkdir -p -- "${project_config%/*}"
  printf '%s\n' "$@" >"${project_config}"
}

test_reading_keeps_values_and_skips_comments() {
  reset_configuration
  write_config '# Options' '' 'tools = rclone uv' '  packages=libssl-dev  ' \
    'mount = ../library' 'mount = /srv/data:rw'
  capture read_project_config
  assert_status 0
  assert_equal 'rclone uv' "${project_options[tools]}"
  assert_equal libssl-dev "${project_options[packages]}"
  assert_array project_mounts ../library /srv/data:rw
}

test_reading_an_empty_value_defines_the_key() {
  reset_configuration
  write_config 'tools ='
  capture read_project_config
  assert_status 0
  assert_equal defined "${project_options[tools]+defined}"
  assert_equal '' "${project_options[tools]}"
}

test_reading_without_a_file_succeeds() {
  reset_configuration
  capture read_project_config
  assert_status 0
  assert_equal 0 "${#project_options[@]}"
}

test_reading_refuses_an_unknown_key() {
  reset_configuration
  write_config '# Options' 'colour = blue'
  capture read_project_config
  assert_status 1
  assert_contains "${errors}" "${project_config}:2: unknown key 'colour'"
}

test_reading_refuses_a_key_set_twice() {
  reset_configuration
  write_config 'tools = uv' 'tools = rclone'
  capture read_project_config
  assert_status 1
  assert_contains "${errors}" "${project_config}:2: 'tools' is set more than once"
}

test_reading_refuses_a_line_without_equals() {
  reset_configuration
  write_config 'tools uv'
  capture read_project_config
  assert_status 1
  assert_contains "${errors}" "${project_config}:1: expected KEY = VALUE"
}

test_saving_creates_the_file_with_a_header() {
  reset_configuration
  capture save_project_option tools 'rclone uv'
  assert_status 0
  assert_file "${project_config}" \
    "# dockered-claude options for this project, saved from the command line
# (see dockered-claude --help).
tools = rclone uv"
  assert_contains "${errors}" "saved 'tools = rclone uv'"
}

test_saving_replaces_the_line_and_keeps_others() {
  reset_configuration
  write_config '# Mine' 'tools = uv' 'packages = gdb'
  capture save_project_option tools rclone
  assert_status 0
  assert_file "${project_config}" $'# Mine\ntools = rclone\npackages = gdb'
}

test_saving_an_empty_value_leaves_no_trailing_space() {
  reset_configuration
  write_config 'tools = uv'
  capture save_project_option tools ''
  assert_status 0
  assert_file "${project_config}" 'tools ='
}

test_saving_an_unchanged_value_writes_nothing() {
  reset_configuration
  project_options[tools]=uv
  capture save_project_option tools uv
  assert_status 0
  assert_equal '' "${errors}"
  [[ ! -e "${project_config}" ]] || fail "expected no file: ${project_config}"
}

test_saving_mounts_replaces_them_where_the_first_was() {
  reset_configuration
  write_config '# Mine' 'mount = /a' 'tools = uv' 'mount = /b:rw'
  mount_paths=(/c /d)
  mount_modes=(["/c"]=ro ["/d"]=rw)
  capture save_project_mounts
  assert_status 0
  assert_file "${project_config}" \
    $'# Mine\nmount = /c\nmount = /d:rw\ntools = uv'
}

test_saving_mounts_keeps_the_paths_as_given() {
  reset_configuration
  write_config 'tools = uv'
  mount_paths=(/real/c)
  mount_modes=(["/real/c"]=rw)
  mount_given_paths=(["/real/c"]=/link/c)
  capture save_project_mounts
  assert_status 0
  assert_file "${project_config}" $'tools = uv\nmount = /link/c:rw'
}

test_saving_no_mounts_removes_them() {
  reset_configuration
  write_config 'mount = /a' 'tools = uv'
  capture save_project_mounts
  assert_status 0
  assert_file "${project_config}" 'tools = uv'
  assert_contains "${errors}" 'removed the mounts'
}

test_saving_in_git_excludes_the_meta_directory() {
  reset_configuration
  git init -q -- "${project_root}"
  capture save_project_option tools uv
  assert_status 0
  assert_equal /.meta/ "$(tail -n 1 -- "${project_root}/.git/info/exclude")"
  assert_contains "${errors}" 'excluded /.meta/ from git'
}

test_finding_walks_up_from_the_working_directory() {
  set_launcher_paths
  HOME="${temporary_directory}/home"
  workdir="${HOME}/a/b"
  mkdir -p -- "${workdir}" "${HOME}/a/${project_config_path%/*}"
  : >"${HOME}/a/${project_config_path}"
  capture find_project_config
  assert_status 0
  assert_equal "${HOME}/a/${project_config_path}" "${project_config}"
}

test_finding_stops_below_home() {
  set_launcher_paths
  HOME="${temporary_directory}/home"
  workdir="${HOME}/a"
  mkdir -p -- "${workdir}" "${HOME}/${project_config_path%/*}"
  : >"${HOME}/${project_config_path}"
  capture find_project_config
  assert_status 0
  assert_equal "${workdir}/${project_config_path}" "${project_config}"
}

test_finding_falls_back_to_the_main_worktree() {
  set_launcher_paths
  HOME="${temporary_directory}/home"
  workdir="${temporary_directory}/repository/sub"
  mkdir -p -- "${HOME}" "${workdir}"
  git init -q -- "${temporary_directory}/repository"
  capture find_project_config
  assert_status 0
  assert_equal "${temporary_directory}/repository/${project_config_path}" \
    "${project_config}"
}

test_reading_keeps_the_profile() {
  reset_configuration
  write_config 'profile = minimal'
  capture read_project_config
  assert_status 0
  assert_equal minimal "${project_options[profile]}"
}

test_saving_keeps_a_given_profile() {
  reset_configuration
  kwargs[profile]=minimal
  capture save_project_options
  assert_status 0
  assert_file "${project_config}" \
    "# dockered-claude options for this project, saved from the command line
# (see dockered-claude --help).
profile = minimal"
}

test_saving_nothing_without_a_given_profile() {
  reset_configuration
  project_options[profile]=minimal
  capture save_project_options
  assert_status 0
  [[ ! -e "${project_config}" ]] || fail "expected no file: ${project_config}"
}
