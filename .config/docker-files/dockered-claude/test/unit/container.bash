# Tests of the docker run arguments of Claude Code's container.
# test/run sources test/lib.bash first,
# which sets launcher and temporary_directory,
# and whose capture sets output, errors and status.
# shellcheck disable=SC2154

# shellcheck source=../../bin/dockered-claude
source -- "${launcher}" || return

# Declare, as globals of the test's subshell,
# the state that run_container's steps read and set,
# with the tools rclone and uv in a launcher directory
# in temporary_directory, uv with an env file,
# and docker answering only for the image's PATH.
reset_container() {
  set_launcher_paths
  declare -ga mounted_tools=() docker_args=() path_entries=() path_suffix=()
  declare -gA tool_volume_names=(
    [uv]=dockered-claude-tool-default-uv-2
    [rclone]=dockered-claude-tool-default-rclone-1
    ["claude-code"]=dockered-claude-tool-default-claude-code-2.1.328
  )
  project_directory="${temporary_directory}/launcher"
  container_image=dockered-claude-default:latest
  mkdir -p -- "${project_directory}"/tools/{rclone,uv,claude-code}
  : >"${project_directory}/tools/claude-code/Dockerfile"
  : >"${project_directory}/tools/rclone/Dockerfile"
  : >"${project_directory}/tools/uv/Dockerfile"
  printf '%s\n' 'UV_CACHE_DIR=/tmp/uv' >"${project_directory}/tools/uv/env"
  # shellcheck disable=SC2329 # Called by add_path_argument.
  docker() {
    [[ "$1 $2" == 'image inspect' ]] || return 1
    printf '%s\n' 'HOME=/home/claude' 'PATH=/usr/local/bin:/usr/bin'
  }
}

test_tools_go_in_front_of_the_image_path_in_order() {
  reset_container
  mounted_tools=(uv rclone)
  capture add_tool_arguments
  assert_status 0
  capture add_path_argument
  assert_status 0
  assert_array docker_args \
    --mount type=volume,src=dockered-claude-tool-default-uv-2,dst=/opt/tools/uv,readonly \
    --mount type=volume,src=dockered-claude-tool-default-rclone-1,dst=/opt/tools/rclone,readonly \
    --env-file "${project_directory}/tools/uv/env" \
    --env PATH=/opt/tools/uv/bin:/opt/tools/rclone/bin:/usr/local/bin:/usr/bin
}

test_without_path_entries_the_image_path_is_kept() {
  reset_container
  capture add_path_argument
  assert_status 0
  assert_array docker_args
}

test_profile_variables_are_passed_and_its_path_follows_the_tools() {
  reset_container
  mounted_tools=(uv)
  declare -ga profile_variables=(SDK_HOME) profile_path_entries=(/opt/sdk/bin)
  capture add_tool_arguments
  assert_status 0
  capture add_profile_arguments
  assert_status 0
  capture add_path_argument
  assert_status 0
  assert_array docker_args \
    --mount type=volume,src=dockered-claude-tool-default-uv-2,dst=/opt/tools/uv,readonly \
    --env-file "${project_directory}/tools/uv/env" \
    --env SDK_HOME \
    --env PATH=/opt/tools/uv/bin:/opt/sdk/bin:/usr/local/bin:/usr/bin
}

test_claude_code_goes_last_on_path_after_the_image() {
  reset_container
  mounted_tools=(uv claude-code)
  declare -ga profile_variables=() profile_path_entries=(/opt/sdk/bin)
  capture add_tool_arguments
  assert_status 0
  capture add_profile_arguments
  assert_status 0
  capture add_path_argument
  assert_status 0
  assert_contains "${docker_args[*]}" \
    '--mount type=volume,src=dockered-claude-tool-default-claude-code-2.1.328,dst=/opt/tools/claude-code,readonly'
  assert_equal \
    PATH=/opt/tools/uv/bin:/opt/sdk/bin:/usr/local/bin:/usr/bin:/opt/tools/claude-code/bin \
    "${docker_args[-1]}"
}

test_claude_code_alone_follows_the_image_path() {
  reset_container
  mounted_tools=(claude-code)
  capture add_tool_arguments
  assert_status 0
  capture add_path_argument
  assert_status 0
  assert_equal PATH=/usr/local/bin:/usr/bin:/opt/tools/claude-code/bin \
    "${docker_args[-1]}"
}

test_claude_code_is_always_mounted_and_last() {
  set_launcher_paths
  declare -ga mounted_tools=()
  tools=(claude-code uv)
  select_mounted_tools
  assert_array mounted_tools uv claude-code
  tools=()
  select_mounted_tools
  assert_array mounted_tools claude-code
}

# Set the paths that add_managed_settings_arguments and run_container read,
# for the profile default, with the user's files under HOME
# and the state in temporary_directory, none of them created.
reset_managed_settings() {
  reset_container
  set_profile default
  HOME="${temporary_directory}/home"
  workdir="${temporary_directory}/work"
  managed_settings_file="${HOME}/.config/dockered-claude/managed-settings.json"
  profile_settings="${project_directory}/profiles/default/managed-settings.json"
  declare -ga mount_paths=()
  declare -gA mount_modes=()
  project_config="${workdir}/${project_config_path}"
  state_dir="${temporary_directory}/state"
  home="${HOME}"
  agents_dir="${HOME}/.agents"
  config_dir="${HOME}/.config/claude"
  git_config_dir="${HOME}/.config/git"
  passwd_file="${state_dir}/etc/passwd"
  group_file="${state_dir}/etc/group"
  uid_host=1000
  gid_host=1000
  mkdir -p -- "${project_directory}/profiles/default" "${workdir}" \
    "${HOME}/.config/dockered-claude"
}

test_managed_settings_are_mounted_only_when_present() {
  reset_managed_settings
  capture add_managed_settings_arguments
  assert_status 0
  assert_array docker_args
}

test_the_users_managed_settings_follow_the_profiles() {
  reset_managed_settings
  printf '{}\n' >"${profile_settings}"
  printf '{}\n' >"${managed_settings_file}"
  capture add_managed_settings_arguments
  assert_status 0
  assert_array docker_args \
    --mount "type=bind,src=${profile_settings},dst=/etc/claude-code/managed-settings.json,readonly" \
    --mount "type=bind,src=${managed_settings_file},dst=/etc/claude-code/managed-settings.d/50-dockered-claude-user.json,readonly"
}

# Run run_container in a subshell, with a docker on PATH
# that prints its arguments, one per line, which exec runs;
# set output to them.
capture_run_container() {
  declare bin="${temporary_directory}/bin"
  mkdir -p -- "${bin}"
  printf '%s\n' '#!/bin/sh' 'printf "%s\n" "$@"' >"${bin}/docker"
  chmod +x -- "${bin}/docker"
  unset -f docker
  output="$(PATH="${bin}:${PATH}" && run_container)"
}

test_managed_settings_in_a_writable_path_are_mounted_read_only() {
  reset_managed_settings
  # The launcher's own repository is the working directory.
  workdir="${project_directory}"
  mkdir -p -- "${temporary_directory}/notes"
  managed_settings_file="${temporary_directory}/notes/managed-settings.json"
  mount_paths=("${temporary_directory}/notes")
  mount_modes["${temporary_directory}/notes"]=rw
  printf '{}\n' >"${profile_settings}"
  printf '{}\n' >"${managed_settings_file}"
  capture_run_container
  assert_contains "${output}" \
    "type=bind,src=${profile_settings},dst=${profile_settings},readonly"
  assert_contains "${output}" \
    "type=bind,src=${managed_settings_file},dst=${managed_settings_file},readonly"
}

test_managed_settings_outside_writable_paths_are_not_mounted_again() {
  reset_managed_settings
  printf '{}\n' >"${profile_settings}"
  printf '{}\n' >"${managed_settings_file}"
  capture_run_container
  [[ "${output}" != *"dst=${profile_settings}"* &&
    "${output}" != *"dst=${managed_settings_file}"* ]] ||
    fail "expected no mount at the files' own paths: ${output}"
}
