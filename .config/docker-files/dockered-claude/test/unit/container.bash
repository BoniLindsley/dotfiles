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
  home=/home/claude
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

test_env_values_starting_with_a_tilde_are_expanded_to_the_home() {
  reset_container
  mounted_tools=(uv)
  printf '%s\n' \
    '# UV_A=~/comment' '' \
    ' UV_CACHE_DIR=~/.cache/uv' \
    'UV_TOOL=~' 'UV_PLAIN=a~/b' 'UV_HOST' 'UV_LAST=~/first' \
    >"${project_directory}/tools/uv/env"
  printf '%s' 'UV_LAST=/last' >>"${project_directory}/tools/uv/env"
  capture add_tool_arguments
  assert_status 0
  assert_array docker_args \
    --mount type=volume,src=dockered-claude-tool-default-uv-2,dst=/opt/tools/uv,readonly \
    --env-file "${project_directory}/tools/uv/env" \
    --env UV_CACHE_DIR=/home/claude/.cache/uv
}

test_an_expanded_env_value_of_a_later_tool_does_not_win() {
  reset_container
  mounted_tools=(uv rclone)
  printf '%s\n' 'SHARED=/uv' 'FIRST=~/uv' >"${project_directory}/tools/uv/env"
  printf '%s\n' 'SHARED=~/rclone' 'FIRST=~/rclone' 'SECOND=~/rclone' \
    >"${project_directory}/tools/rclone/env"
  capture add_tool_arguments
  assert_status 0
  assert_array docker_args \
    --mount type=volume,src=dockered-claude-tool-default-uv-2,dst=/opt/tools/uv,readonly \
    --mount type=volume,src=dockered-claude-tool-default-rclone-1,dst=/opt/tools/rclone,readonly \
    --env-file "${project_directory}/tools/rclone/env" \
    --env-file "${project_directory}/tools/uv/env" \
    --env FIRST=/home/claude/uv \
    --env SECOND=/home/claude/rclone
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
  user_config="${HOME}/.config/dockered-claude/config"
  profile_settings="${project_directory}/profiles/default/managed-settings.json"
  declare -ga mount_paths=()
  declare -gA mount_modes=()
  project_config="${workdir}/${project_config_path}"
  state_dir="${temporary_directory}/state"
  claude_state="${state_dir}/tools/claude-code/.claude"
  home="${HOME}"
  agents_dir="${HOME}/.agents"
  config_dir="${HOME}/.config/claude"
  git_config_dir="${HOME}/.config/git"
  declare -ga run_links=() persisted_paths=()
  declare -gA link_targets=() persisted_bases=()
  username=claude
  groupname=staff
  uid_host=1000
  gid_host=1001
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
# that records each command but docker run in calls,
# gives the base image the ID sha256:base,
# saves the Dockerfile and the listing of run.tar of a build in build,
# and gives the run image the ID sha256:run;
# docker run prints its arguments, one per line,
# and exits with FAKE_RUN_STATUS, or 0.
# FAKE_BUILD_SIGNAL, if set, is sent to the launcher during the build,
# and FAKE_BUILD_STATUS, if set, fails the build with it.
# Set output to what docker run printed, and status to that of run_container.
capture_run_container() {
  declare bin="${temporary_directory}/bin"
  calls="${temporary_directory}/calls"
  build="${temporary_directory}/build"
  mkdir -p -- "${bin}"
  : >"${calls}"
  cat >"${bin}/docker" <<'DOCKER'
#!/usr/bin/env bash
case "$1" in
run)
  printf '%s\n' "$@"
  exit "${FAKE_RUN_STATUS:-0}"
  ;;
build)
  printf '%s\n' "docker $*" >>"${calls}"
  context="${!#}"
  while (($#)); do
    [[ "$1" != --iidfile ]] || id_file="$2"
    shift
  done
  { cat -- "${context}/Dockerfile" &&
    tar --list --verbose --numeric-owner --file "${context}/run.tar" |
    awk '{ $3 = $4 = $5 = ""; print }' | tr -s ' '; } >"${build}"
  [[ -z "${FAKE_BUILD_SIGNAL:-}" ]] || kill -s "${FAKE_BUILD_SIGNAL}" "${PPID}"
  [[ -z "${FAKE_BUILD_STATUS:-}" ]] || exit "${FAKE_BUILD_STATUS}"
  printf 'sha256:run' >"${id_file}"
  ;;
image)
  printf '%s\n' "docker $*" >>"${calls}"
  [[ "$2" != inspect ]] || printf 'sha256:base\n'
  ;;
*) exit 1 ;;
esac
DOCKER
  chmod +x -- "${bin}/docker"
  unset -f docker
  export calls build
  status=0
  output="$(PATH="${bin}:${PATH}" && run_container)" || status=$?
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

test_pinned_tools_are_mounted_by_name() {
  declare -ga tools=(uv:3 claude-code:7 rclone)
  declare -ga mounted_tools=()
  declare -gA tool_pins=()
  select_mounted_tools
  assert_array mounted_tools uv rclone claude-code
  assert_equal 3 "${tool_pins[uv]}"
  assert_equal 7 "${tool_pins["claude-code"]}"
  assert_equal '' "${tool_pins[rclone]:-}"
}

# Print calls with the temporary directory of the build as DIR.
read_calls() {
  sed 's#/[^ ]*/tmp\.[[:alnum:]]*#DIR#g' -- "${calls}"
}

test_the_run_image_is_built_from_the_image_and_removed_after() {
  reset_managed_settings
  capture_run_container
  assert_status 0
  assert_equal "docker image prune --force --filter label=dockered-claude.run=1 --filter until=10m
docker image inspect --format {{.Id}} dockered-claude-default:latest
docker build --build-arg BASE_IMAGE_ID=sha256:base --iidfile DIR/id --label dockered-claude.run=1 --label dockered-claude.profile=default --quiet DIR/context
docker image rm sha256:run" "$(read_calls)"
  assert_equal sha256:run "${output##*$'\n'}"
}

test_the_run_image_adds_the_identity_and_the_home() {
  reset_managed_settings
  capture_run_container
  assert_status 0
  assert_file "${build}" "ARG BASE_IMAGE_ID
FROM \${BASE_IMAGE_ID}
ADD run.tar /
-rw-r--r-- 0/0 etc/passwd
-rw-r--r-- 0/0 etc/group
drwx------ 1000/1001 ${home#/}/
drwxr-xr-x 1000/1001 ${home#/}/.config/"
  [[ "${output}" != *etc/passwd* && "${output}" != *etc/group* ]] ||
    fail "expected no mount of /etc files: ${output}"
}

test_the_identity_names_root_and_the_user() {
  reset_managed_settings
  capture write_user_identity "${temporary_directory}/root"
  assert_status 0
  assert_file "${temporary_directory}/root/etc/passwd" "root:x:0:0:root:/root:/bin/bash
claude:x:1000:1001:claude:${home}:/bin/bash"
  assert_file "${temporary_directory}/root/etc/group" $'root:x:0:\nstaff:x:1001:'
}

test_the_container_status_is_returned_after_removing_the_image() {
  reset_managed_settings
  FAKE_RUN_STATUS=3 capture_run_container
  assert_status 3
  assert_contains "$(read_calls)" 'docker image rm sha256:run'
}

test_a_failed_build_runs_nothing() {
  reset_managed_settings
  FAKE_BUILD_STATUS=2 capture_run_container
  assert_status 1
  assert_equal '' "${output}"
  [[ "$(read_calls)" != *'image rm'* ]] || fail "expected no removal"
}

test_an_interrupt_during_the_build_removes_the_image_without_running() {
  reset_managed_settings
  FAKE_BUILD_SIGNAL=INT capture_run_container
  assert_status 130
  assert_equal '' "${output}"
  assert_contains "$(read_calls)" 'docker image rm sha256:run'
}

test_the_run_image_adds_the_links_after_the_home_directories() {
  reset_managed_settings
  run_links=("${home}/src" /1/2 "${home}/a/b/c")
  link_targets=(["${home}/src"]=/data/src ["/1/2"]=/b ["${home}/a/b/c"]=../../x)
  capture_run_container
  assert_status 0
  assert_equal "-rw-r--r-- 0/0 etc/passwd
-rw-r--r-- 0/0 etc/group
drwx------ 1000/1001 ${home#/}/
drwxr-xr-x 1000/1001 ${home#/}/.config/
drwxr-xr-x 1000/1001 ${home#/}/a/
drwxr-xr-x 1000/1001 ${home#/}/a/b/
lrwxrwxrwx 0/0 ${home#/}/src -> /data/src
lrwxrwxrwx 0/0 1/2 -> /b
lrwxrwxrwx 0/0 ${home#/}/a/b/c -> ../../x" "$(sed 1,3d -- "${build}")"
}

test_persisted_paths_are_mounted_from_the_state_over_a_cache_tmpfs() {
  reset_managed_settings
  persisted_paths=(.claude .cache/uv .config/rclone)
  persisted_bases=(
    [".claude"]="${state_dir}/tools/claude-code"
    [".cache/uv"]="${state_dir}/tools/uv"
    [".config/rclone"]="${state_dir}/tools/rclone"
  )
  capture_run_container
  assert_status 0
  assert_contains "${output}" "CLAUDE_CONFIG_DIR=${home}/.claude"
  assert_contains "${output}" "--tmpfs
${home}/.cache:rw,exec,nosuid,nodev,uid=1000,gid=1001,mode=0700"
  assert_contains "${output}" "--mount
type=bind,src=${claude_state},dst=${home}/.claude
--mount
type=bind,src=${state_dir}/tools/uv/.cache/uv,dst=${home}/.cache/uv
--mount
type=bind,src=${state_dir}/tools/rclone/.config/rclone,dst=${home}/.config/rclone"
  [[ "${output}" != *dst=/home$'\n'* ]] || fail "expected no /home mount"
}

test_the_run_image_makes_the_directories_above_mount_points_in_the_home() {
  reset_managed_settings
  workdir="${home}/src/project"
  mount_paths=("${home}/notes/today" /srv/data)
  mount_modes=(["${home}/notes/today"]=ro ["/srv/data"]=ro)
  persisted_paths=(.local/share/uv)
  persisted_bases=([".local/share/uv"]="${state_dir}/tools/uv")
  capture_run_container
  assert_status 0
  assert_equal "-rw-r--r-- 0/0 etc/passwd
-rw-r--r-- 0/0 etc/group
drwx------ 1000/1001 ${home#/}/
drwxr-xr-x 1000/1001 ${home#/}/.config/
drwxr-xr-x 1000/1001 ${home#/}/.local/
drwxr-xr-x 1000/1001 ${home#/}/.local/share/
drwxr-xr-x 1000/1001 ${home#/}/notes/
drwxr-xr-x 1000/1001 ${home#/}/src/" "$(sed 1,3d -- "${build}")"
}

test_the_user_configuration_in_a_writable_path_is_mounted_read_only() {
  reset_managed_settings
  mount_paths=("${HOME}")
  mount_modes["${HOME}"]=rw
  capture_run_container
  assert_status 0
  assert_contains "${output}" \
    "type=bind,src=${user_config%/*},dst=${user_config%/*},readonly"
}
