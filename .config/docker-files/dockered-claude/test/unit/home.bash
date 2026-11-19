# Tests of the persisted home paths:
# selecting them from the tools and the profile,
# checking them, and preparing them in the state directory.
# test/run sources test/lib.bash first,
# which sets launcher and temporary_directory,
# and whose capture sets output, errors and status.
# shellcheck disable=SC2154

# shellcheck source=../../bin/dockered-claude
source -- "${launcher}" || return

# Declare, as globals of the test's subshell,
# the state that the launcher's run declares for persisted paths,
# with a launcher directory and the state in temporary_directory,
# the tools node and uv, and the profile default without a launcher.bash.
reset_home() {
  set_launcher_paths
  declare -ga mounted_tools=(node claude-code) persisted_paths=() user_persists=()
  declare -gA persisted_kinds=() persisted_bases=() persisted_sources=()
  project_directory="${temporary_directory}/launcher"
  state_dir="${temporary_directory}/state"
  persists_home="${state_dir}/persists/home/someone"
  user_config="${temporary_directory}/user/config"
  home=/home/someone
  workdir=/home/someone/project
  profile=default
  mkdir -p -- "${project_directory}"/tools/{node,uv,claude-code} \
    "${project_directory}/profiles/default"
  printf '%s\n' '# Comment' '' '.npm/' >"${project_directory}/tools/node/home"
  printf '%s\n' .cache/uv/ .local/share/uv/ >"${project_directory}/tools/uv/home"
  printf '%s\n' .claude/ >"${project_directory}/tools/claude-code/home"
}

# Write a launcher.bash for the profile default
# whose profile_home prints the arguments.
write_profile_home() {
  declare script="${project_directory}/profiles/default/launcher.bash"
  printf 'profile_home() {\n' >"${script}"
  printf '  printf "%%s\\n" %q\n' "$@" >>"${script}"
  printf '}\n' >>"${script}"
}

test_valid_home_paths_are_files_or_directories() {
  reset_home
  validate_home_path .npm/
  assert_equal .npm "${home_path}"
  assert_equal directory "${home_kind}"
  validate_home_path .config/tool/settings.json
  assert_equal .config/tool/settings.json "${home_path}"
  assert_equal file "${home_kind}"
}

test_invalid_home_paths_are_refused() {
  reset_home
  declare spec
  for spec in '' / /etc/ ../x a//b ./a a/./b a/../b a/.. 'a,b' 'a"b' $'a\nb'; do
    capture validate_home_path "${spec}"
    assert_status 1
    assert_contains "${errors}" 'it must be relative to ~, normalized'
  done
}

test_selecting_takes_the_tools_then_the_profile() {
  reset_home
  mounted_tools=(uv node uv claude-code)
  write_profile_home .gradle/ .m2/settings.xml
  capture select_persisted_paths
  assert_status 0
  assert_array persisted_paths .cache/uv .local/share/uv .npm .claude \
    .gradle .m2/settings.xml
  assert_equal "${state_dir}/tools/uv" "${persisted_bases[".cache/uv"]}"
  assert_equal "${state_dir}/tools/claude-code" "${persisted_bases[".claude"]}"
  assert_equal "${state_dir}/profiles/default" "${persisted_bases[".gradle"]}"
  assert_equal file "${persisted_kinds[".m2/settings.xml"]}"
  assert_equal directory "${persisted_kinds[".gradle"]}"
  assert_equal "${project_directory}/profiles/default/launcher.bash: profile_home" \
    "${persisted_sources[".gradle"]}"
}

test_overlapping_persisted_paths_are_refused_naming_both() {
  reset_home
  write_profile_home .npm/cache/
  capture select_persisted_paths
  assert_status 1
  assert_equal "${script_name}: ${project_directory}/profiles/default/launcher.bash: profile_home: cannot persist /home/someone/.npm/cache: it is at, inside or above /home/someone/.npm, persisted by ${project_directory}/tools/node/home" \
    "${errors}"
  reset_home
  write_profile_home .claude/
  capture select_persisted_paths
  assert_status 1
  assert_contains "${errors}" 'it is at, inside or above /home/someone/.claude'
}

test_the_cache_and_what_the_launcher_mounts_cannot_persist() {
  reset_home
  declare spec
  for spec in .config/ .config/git/x .agents/; do
    write_profile_home "${spec}"
    persisted_paths=()
    capture select_persisted_paths
    assert_status 1
    assert_contains "${errors}" 'which the launcher mounts'
  done
  write_profile_home .cache/
  persisted_paths=()
  capture select_persisted_paths
  assert_status 1
  assert_contains "${errors}" 'the launcher mounts a tmpfs there'
}

test_the_tools_home_files_go_together() {
  reset_home
  project_directory="${repository}"
  mounted_tools=(node uv vcpkg rclone claude-code)
  capture select_persisted_paths
  assert_status 0
  assert_array persisted_paths .npm .cache/uv .local/share/uv .cache/vcpkg \
    .config/rclone .claude
}

test_the_working_directory_must_not_overlap_a_persisted_path() {
  reset_home
  persisted_paths=(.npm .claude)
  declare path
  for path in /home/someone/.npm /home/someone/.npm/x /home/someone /; do
    workdir="${path}"
    capture check_working_directory
    assert_status 1
    assert_contains "${errors}" "cannot run in '${path}'"
  done
  workdir=/home/someone/.npmrc.d
  capture check_working_directory
  assert_status 0
}

test_preparing_creates_directories_and_files_privately() {
  reset_home
  persisted_paths=(.npm .m2/settings.xml)
  persisted_kinds=([".npm"]=directory [".m2/settings.xml"]=file)
  persisted_bases=(
    [".npm"]="${state_dir}/tools/node"
    [".m2/settings.xml"]="${state_dir}/profiles/default"
  )
  capture prepare_persisted_paths
  assert_status 0
  [[ -d "${state_dir}/tools/node/.npm" ]] || fail "expected a directory"
  assert_file "${state_dir}/profiles/default/.m2/settings.xml" ''
  assert_equal 700 "$(stat -c %a -- "${state_dir}/tools/node")"
  assert_equal 700 "$(stat -c %a -- "${state_dir}/profiles")"
}

test_preparing_keeps_what_is_there() {
  reset_home
  persisted_paths=(.npm .m2/settings.xml)
  persisted_kinds=([".npm"]=directory [".m2/settings.xml"]=file)
  persisted_bases=([".npm"]="${state_dir}/x" [".m2/settings.xml"]="${state_dir}/x")
  mkdir -p -- "${state_dir}/x/.npm" "${state_dir}/x/.m2"
  printf 'kept\n' >"${state_dir}/x/.npm/file"
  printf '<settings/>\n' >"${state_dir}/x/.m2/settings.xml"
  capture prepare_persisted_paths
  assert_status 0
  assert_file "${state_dir}/x/.npm/file" kept
  assert_file "${state_dir}/x/.m2/settings.xml" '<settings/>'
}

test_preparing_refuses_the_other_kind() {
  reset_home
  persisted_paths=(.npm)
  persisted_kinds=([".npm"]=directory)
  persisted_bases=([".npm"]="${state_dir}/x")
  mkdir -p -- "${state_dir}/x"
  : >"${state_dir}/x/.npm"
  capture prepare_persisted_paths
  assert_status 1
  assert_contains "${errors}" "${state_dir}/x/.npm is not a directory"
  persisted_kinds=([".npm"]=file)
  rm -- "${state_dir}/x/.npm"
  mkdir -- "${state_dir}/x/.npm"
  capture prepare_persisted_paths
  assert_status 1
  assert_contains "${errors}" "${state_dir}/x/.npm is not a file"
}

test_the_users_persisted_paths_come_last_and_are_shared() {
  reset_home
  write_profile_home .gradle/
  user_persists=(.bash_history notes/)
  capture select_persisted_paths
  assert_status 0
  assert_array persisted_paths .npm .claude .gradle .bash_history notes
  assert_equal "${persists_home}" "${persisted_bases[".bash_history"]}"
  assert_equal directory "${persisted_kinds[notes]}"
  assert_equal "${user_config}" "${persisted_sources[notes]}"
  user_persists=(.npm/)
  persisted_paths=()
  capture select_persisted_paths
  assert_status 1
  assert_contains "${errors}" "${user_config}: cannot persist /home/someone/.npm"
}
