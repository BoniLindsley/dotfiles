# Tests of the clean command,
# with a fake docker whose listings are set by each test.
# test/run sources test/lib.bash first,
# which sets launcher and temporary_directory,
# and whose capture sets output, errors and status.
# shellcheck disable=SC2154

# shellcheck source=../../bin/dockered-claude
source -- "${launcher}" || return

# Declare, as globals of the test's subshell,
# the arrays that the launcher's main declares,
# with the profile default and the tool uv defined
# in a launcher directory in temporary_directory,
# and empty listings for the fake docker.
reset_clean() {
  set_launcher_paths
  declare -gA kwargs=([command]=clean)
  declare -ga args=()
  project_directory="${temporary_directory}/launcher"
  calls="${temporary_directory}/calls"
  mkdir -p -- "${project_directory}/profiles/default" \
    "${project_directory}/tools/uv"
  : >"${project_directory}/profiles/default/Dockerfile"
  : >"${project_directory}/tools/uv/Dockerfile"
  : >"${calls}"
  fake_stopped_containers=''
  fake_fill_containers=''
  fake_volume_listing=''
  fake_packages_listing=''
  fake_profile_listing=''
  fake_old_listing=''
  fake_current_image=''
  declare -gA fake_users_of=() fake_image_labels=() fake_failing=()
}

# A fake docker for the commands clean uses.
# Listings come from the variables reset_clean sets,
# the containers using something from fake_users_of, by filter,
# the labels of an image from fake_image_labels, by ID,
# and removals are recorded in calls, fake_failing for those in fake_failing.
docker() {
  declare reference="${!#}"
  case "$*" in
  'ps --all --quiet --filter '*) printf '%s' "${fake_users_of[${reference}]:-}" ;;
  *'--filter label=dockered-claude.profile --format {{.ID}} {{.Names}}'*)
    printf '%s' "${fake_stopped_containers}"
    ;;
  *'--filter name=dockered-claude-tool- --format {{.ID}} {{.Names}}'*)
    printf '%s' "${fake_fill_containers}"
    ;;
  'volume ls '*) printf '%s' "${fake_volume_listing}" ;;
  'image ls --quiet '*)
    [[ -z "${fake_packages_listing}" ]] || cut -d ' ' -f 1 <<<"${fake_packages_listing}"
    ;;
  *'--filter label=dockered-claude.packages --format'*)
    printf '%s' "${fake_packages_listing}"
    ;;
  *'--filter label=dockered-claude.profile --format'*)
    printf '%s' "${fake_profile_listing}"
    ;;
  *' dockered-claude') printf '%s' "${fake_old_listing}" ;;
  'image inspect --format {{.Id}} '*)
    [[ -n "${fake_current_image}" ]] || return 1
    printf '%s\n' "${fake_current_image}"
    ;;
  'image inspect --format '*) printf '%s\n' "${fake_image_labels[${reference}]}" ;;
  'rm '* | 'volume rm '* | 'image rm '*)
    printf '%s\n' "$*" >>"${calls}"
    [[ -z "${fake_failing[${reference}]+defined}" ]]
    ;;
  *) return 1 ;;
  esac
}

test_dry_run_lists_without_removing() {
  reset_clean
  kwargs[dry_run]=1
  args=(tools)
  fake_volume_listing=$'uv/default/1/dockered-claude-tool-default-uv-1\nuv/default/2/dockered-claude-tool-default-uv-2\n'
  capture clean_unused
  assert_status 0
  assert_equal \
    "volume dockered-claude-tool-default-uv-1: older generation of tool 'uv' for profile 'default'" \
    "${output}"
  assert_file "${calls}" ''
}

test_removes_only_what_is_confirmed() {
  reset_clean
  args=(tools)
  fake_volume_listing=$'uv/default/1/dockered-claude-tool-default-uv-1\nuv/default/2/dockered-claude-tool-default-uv-2\nuv/default/3/dockered-claude-tool-default-uv-3\n'
  capture clean_unused <<<$'y\nn'
  assert_status 0
  assert_file "${calls}" 'volume rm dockered-claude-tool-default-uv-1'
  assert_contains "${errors}" \
    "remove volume dockered-claude-tool-default-uv-1 (older generation of tool 'uv' for profile 'default')? [y/N]"
  assert_contains "${errors}" 'removed volume dockered-claude-tool-default-uv-1'
}

test_end_of_input_removes_nothing() {
  reset_clean
  args=(tools)
  fake_volume_listing=$'uv/default/1/dockered-claude-tool-default-uv-1\nuv/default/2/dockered-claude-tool-default-uv-2\n'
  capture clean_unused </dev/null
  assert_status 0
  assert_file "${calls}" ''
}

test_a_failed_removal_fails_after_the_rest() {
  reset_clean
  args=(tools)
  fake_volume_listing=$'uv/default/1/dockered-claude-tool-default-uv-1\nuv/default/2/dockered-claude-tool-default-uv-2\nuv/default/3/dockered-claude-tool-default-uv-3\n'
  fake_failing["dockered-claude-tool-default-uv-1"]=1
  capture clean_unused <<<$'y\ny'
  assert_status 1
  assert_file "${calls}" \
    $'volume rm dockered-claude-tool-default-uv-1\nvolume rm dockered-claude-tool-default-uv-2'
}

test_tools_keeps_the_newest_and_what_containers_use() {
  reset_clean
  mkdir -p -- "${project_directory}/profiles/minimal"
  : >"${project_directory}/profiles/minimal/Dockerfile"
  kwargs[dry_run]=1
  args=(tools)
  fake_volume_listing=$'uv/default/9/dockered-claude-tool-default-uv-9\nuv/default/10/dockered-claude-tool-default-uv-10\nuv/default/8/dockered-claude-tool-default-uv-8\nuv/minimal/1/dockered-claude-tool-minimal-uv-1\n'
  fake_users_of["volume=dockered-claude-tool-default-uv-8"]=container
  capture clean_unused
  assert_status 0
  assert_equal \
    "volume dockered-claude-tool-default-uv-9: older generation of tool 'uv' for profile 'default'" \
    "${output}"
}

test_tools_offers_volumes_of_what_is_no_longer_defined() {
  reset_clean
  kwargs[dry_run]=1
  args=(tools)
  fake_volume_listing=$'rclone/default/1/dockered-claude-tool-default-rclone-1\nuv/gone/1/dockered-claude-tool-gone-uv-1\n///dockered-claude-tool-uv\n///unrelated-dockered-claude-tool-x\n'
  capture clean_unused
  assert_status 0
  assert_equal \
    $'volume dockered-claude-tool-default-rclone-1: tool \'rclone\' is no longer defined\nvolume dockered-claude-tool-gone-uv-1: profile \'gone\' is no longer defined\nvolume dockered-claude-tool-uv: from an earlier version of the launcher' \
    "${output}"
}

test_containers_offers_stopped_and_fill_containers() {
  reset_clean
  kwargs[dry_run]=1
  args=(containers)
  fake_stopped_containers=$'c1 quirky_name dockered-claude-default:latest\n'
  fake_fill_containers=$'c2 dockered-claude-tool-default-uv-3-fill sha256:tool\nc3 dockered-claude-tool-notes sha256:other\n'
  capture clean_unused
  assert_status 0
  assert_equal \
    $'container quirky_name: stopped, of image dockered-claude-default:latest\ncontainer dockered-claude-tool-default-uv-3-fill: left from filling dockered-claude-tool-default-uv-3' \
    "${output}"
}

test_packages_says_how_each_image_stands() {
  reset_clean
  kwargs[dry_run]=1
  args=(packages)
  fake_packages_listing=$'sha256:p1 dockered-claude-default:packages-aaa\nsha256:p2 dockered-claude-default:packages-bbb\nsha256:p3 <none>:<none>\nsha256:p4 dockered-claude-gone:packages-ccc\nsha256:p5 dockered-claude-default:packages-ddd\n'
  fake_image_labels["sha256:p1"]='sha256:base|gdb'
  fake_image_labels["sha256:p2"]='sha256:old|gdb strace'
  fake_image_labels["sha256:p3"]='sha256:old|gdb'
  fake_image_labels["sha256:p4"]='|curl'
  fake_users_of["ancestor=sha256:p5"]=container
  fake_current_image=sha256:base
  capture clean_unused
  assert_status 0
  assert_equal \
    $'image dockered-claude-default:packages-aaa: packages gdb; current for profile \'default\'\nimage dockered-claude-default:packages-bbb: packages gdb strace; built from an older image of profile \'default\'\nimage sha256:p3: packages gdb; replaced by a later build\nimage dockered-claude-gone:packages-ccc: packages curl; profile \'gone\' is no longer defined' \
    "${output}"
}

test_profiles_offers_replaced_undefined_and_old_images() {
  reset_clean
  kwargs[dry_run]=1
  args=(profiles)
  fake_packages_listing=$'sha256:p1 <none>:<none>\n'
  fake_profile_listing=$'sha256:i1 dockered-claude-default:latest\nsha256:i2 <none>:<none>\nsha256:i3 dockered-claude-gone:latest\nsha256:p1 <none>:<none>\nsha256:i4 <none>:<none>\nsha256:i5 dockered-claude:latest\n'
  fake_old_listing=$'sha256:i5 dockered-claude:latest\nsha256:i6 dockered-claude:minimal\n'
  fake_users_of["ancestor=sha256:i4"]=container
  capture clean_unused
  assert_status 0
  assert_equal \
    $'image sha256:i2: replaced by a later build\nimage dockered-claude-gone:latest: profile \'gone\' is no longer defined\nimage dockered-claude:latest: from an earlier version of the launcher\nimage dockered-claude:minimal: from an earlier version of the launcher' \
    "${output}"
}

test_all_cleans_containers_first() {
  reset_clean
  args=(all)
  fake_stopped_containers=$'c1 quirky_name dockered-claude-default:latest\n'
  fake_volume_listing=$'uv/default/1/dockered-claude-tool-default-uv-1\nuv/default/2/dockered-claude-tool-default-uv-2\n'
  capture clean_unused <<<$'y\ny'
  assert_status 0
  assert_file "${calls}" \
    $'rm quirky_name\nvolume rm dockered-claude-tool-default-uv-1'
}

test_says_when_there_is_nothing_to_clean() {
  reset_clean
  args=(all)
  capture clean_unused
  assert_status 0
  assert_contains "${errors}" 'nothing to clean'
}

test_the_command_runs_clean() {
  reset_clean
  # shellcheck disable=SC2329 # Called by run.
  clean_unused() { printf 'clean_unused %s\n' "${args[*]}" >>"${calls}"; }
  HOME="${temporary_directory}"
  parse_arguments clean --list tools
  capture run
  assert_status 0
  assert_file "${calls}" 'clean_unused tools'
}
