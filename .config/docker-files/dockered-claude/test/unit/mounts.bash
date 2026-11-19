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
  declare -gA mount_given_paths=() link_targets=() link_climbs=()
  declare -ga mounts=() project_mounts=() mount_paths=() link_paths=()
  declare -ga persisted_paths=(.claude .cache/uv)
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

test_normalizing_drops_dots_and_dot_dots_after_directories() {
  reset_mounts
  normalize_path /a/./b//c/../d/
  assert_equal /a/b/d "${normalized_path}"
}

test_normalizing_keeps_dot_dot_after_a_symbolic_link() {
  reset_mounts
  mkdir -p -- "${temporary_directory}/x/y"
  ln -s -- x/y "${temporary_directory}/l"
  normalize_path "${temporary_directory}/l/../z"
  assert_equal "${temporary_directory}/l/../z" "${normalized_path}"
}

test_normalizing_stops_at_the_root() {
  reset_mounts
  normalize_path /../a/..
  assert_equal / "${normalized_path}"
}

test_resolving_keeps_the_path_as_given() {
  reset_mounts
  mkdir -- "${temporary_directory}/target"
  ln -s -- target "${temporary_directory}/link"
  resolve_mount_spec ./link/ "${temporary_directory}"
  assert_equal "${temporary_directory}/link" "${mount_given}"
}

# Make the design's example under temporary_directory, as t:
# t/1/2 -> t/b, t/b/3/4 -> t/d (relative), t/d/5/6 -> t/f.
make_link_chain() {
  declare t="${temporary_directory}"
  mkdir -p -- "${t}"/{1,b/3,d/5,f}
  ln -s -- "${t}/b" "${t}/1/2"
  ln -s -- ../../d "${t}/b/3/4"
  ln -s -- "${t}/f" "${t}/d/5/6"
}

test_tracing_records_every_link_on_the_way() {
  reset_mounts
  make_link_chain
  declare t="${temporary_directory}"
  trace_links "${t}/1/2/3/4/5/6"
  assert_equal "${t}/f" "${traced_path}"
  assert_array link_paths "${t}/1/2" "${t}/b/3/4" "${t}/d/5/6"
  assert_equal "${t}/b" "${link_targets["${t}/1/2"]}"
  assert_equal ../../d "${link_targets["${t}/b/3/4"]}"
  assert_equal "${t}/f" "${link_targets["${t}/d/5/6"]}"
}

test_tracing_follows_links_inside_a_target() {
  reset_mounts
  declare t="${temporary_directory}"
  mkdir -p -- "${t}/real/sub"
  ln -s -- real "${t}/inner"
  ln -s -- inner/sub "${t}/outer"
  trace_links "${t}/outer"
  assert_equal "${t}/real/sub" "${traced_path}"
  assert_array link_paths "${t}/outer" "${t}/inner"
}

test_tracing_agrees_with_realpath() {
  reset_mounts
  make_link_chain
  declare path="${temporary_directory}/1/2/3/4/../4/5/6/missing"
  trace_links "${path}"
  assert_equal "$(realpath -m -- "${path}")" "${traced_path}"
}

test_tracing_records_a_link_once() {
  reset_mounts
  make_link_chain
  trace_links "${temporary_directory}/1/2/3"
  trace_links "${temporary_directory}/1/2"
  assert_array link_paths "${temporary_directory}/1/2"
}

test_tracing_fails_on_a_loop() {
  reset_mounts
  ln -s -- loop "${temporary_directory}/loop"
  capture trace_links "${temporary_directory}/loop"
  assert_status 1
  assert_contains "${errors}" 'more than 40 symbolic links'
}

test_tracing_fails_on_a_target_with_a_newline() {
  reset_mounts
  ln -s -- $'a\nb' "${temporary_directory}/odd"
  capture trace_links "${temporary_directory}/odd"
  assert_status 1
  assert_contains "${errors}" 'has an empty target or one with a newline'
}

test_tracing_the_working_directory_uses_pwd() {
  reset_mounts
  make_link_chain
  cd -- "${temporary_directory}/1/2/3"
  workdir="$(pwd -P)"
  trace_working_directory
  assert_array link_paths "${temporary_directory}/1/2"
}

test_tracing_the_working_directory_skips_a_stale_pwd() {
  reset_mounts
  make_link_chain
  workdir="${temporary_directory}/f"
  PWD="${temporary_directory}/1/2"
  trace_working_directory
  assert_array link_paths
}

test_a_climb_out_of_a_missing_directory_warns() {
  reset_mounts
  declare t="${temporary_directory}"
  mkdir -p -- "${t}/archive" "${t}/work/proj" "${t}/data"
  ln -s -- ../archive/../work/proj "${t}/data/proj"
  trace_links "${t}/data/proj"
  mount_paths=("${t}/work/proj")
  capture warn_missing_climbed_directories
  assert_contains "${errors}" \
    "'${t}/data/proj' leaves '${t}/archive' with '..'"
  assert_array link_paths "${t}/data/proj"
  assert_equal ../archive/../work/proj "${link_targets["${t}/data/proj"]}"
}

test_a_climb_out_of_a_directory_the_container_has_is_quiet() {
  reset_mounts
  make_link_chain
  trace_links "${temporary_directory}/1/2/3/4/5/6"
  mount_paths=("${temporary_directory}/f")
  capture warn_missing_climbed_directories
  assert_equal '' "${errors}"
}

test_adding_a_mount_traces_it_and_keeps_the_path_given() {
  reset_selection
  make_link_chain
  resolve_mount_spec "${temporary_directory}/1/2/3" /
  add_mount
  assert_array mount_paths "${temporary_directory}/b/3"
  assert_equal "${temporary_directory}/1/2/3" \
    "${mount_given_paths["${temporary_directory}/b/3"]}"
  assert_array link_paths "${temporary_directory}/1/2"
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

test_checking_refuses_a_persisted_path_inside_the_cache() {
  reset_mounts
  capture check_mount_path /home/someone/.cache/uv
  assert_status 1
  assert_contains "${errors}" 'it would replace /home/someone/.cache/uv'
}

test_checking_refuses_the_cache_but_allows_inside_it() {
  reset_mounts
  capture check_mount_path /home/someone/.cache
  assert_status 1
  assert_contains "${errors}" "it would replace the run's own ~/.cache"
  capture check_mount_path /home/someone/.cache/pip
  assert_status 0
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
    resolve_mount_spec "${spec}" /
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

test_links_inside_mounts_are_not_made() {
  reset_mounts
  mount_paths=(/srv/data)
  link_paths=(/srv/data/current /home/someone/project/lib /srv/other /1/2)
  capture select_run_links
  assert_status 0
  assert_equal '' "${errors}"
  assert_array run_links /srv/other /1/2
}

test_links_at_inside_or_above_reserved_paths_are_refused() {
  reset_mounts
  link_paths=(
    /opt /usr/lib64 /home /home/someone /home/someone/.config
    /home/someone/.claude/projects /home/someone/.cache/pip
    /home/someone/src /srv/data
  )
  capture select_run_links
  assert_status 0
  assert_array run_links /home/someone/src /srv/data
  assert_equal "${script_name}: not making the symbolic link '/opt' in the container: it is at, inside or above /opt/tools
${script_name}: not making the symbolic link '/usr/lib64' in the container: it is at, inside or above /usr
${script_name}: not making the symbolic link '/home' in the container: it is at, inside or above /home/someone/.claude
${script_name}: not making the symbolic link '/home/someone' in the container: it is at, inside or above /home/someone/.claude
${script_name}: not making the symbolic link '/home/someone/.config' in the container: it is at, inside or above /home/someone/.config/claude
${script_name}: not making the symbolic link '/home/someone/.claude/projects' in the container: it is at, inside or above /home/someone/.claude
${script_name}: not making the symbolic link '/home/someone/.cache/pip' in the container: it is at, inside or above /home/someone/.cache" \
    "${errors}"
}
