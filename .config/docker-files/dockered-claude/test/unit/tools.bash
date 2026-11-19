# Tests of building, finding and mounting generations of tool volumes,
# with a fake docker that keeps volumes as files of labels.
# test/run sources test/lib.bash first,
# which sets launcher and temporary_directory,
# and whose capture sets output, errors and status.
# shellcheck disable=SC2154

# shellcheck source=../../bin/dockered-claude
source -- "${launcher}" || return

# Declare, as globals of the test's subshell,
# the state that the tool functions read and set,
# for generation 1 of the profile default, with the image ID sha256:base,
# with the tools uv and rclone defined
# in a launcher directory in temporary_directory,
# and the fake docker's volumes, containers and calls in it.
reset_tools() {
  set_launcher_paths
  declare -ga mounted_tools=()
  declare -gA tool_volume_names=() tool_pins=()
  project_directory="${temporary_directory}/launcher"
  volumes="${temporary_directory}/volumes"
  containers="${temporary_directory}/containers"
  calls="${temporary_directory}/calls"
  mkdir -p -- "${project_directory}"/tools/{uv,rclone} \
    "${project_directory}/profiles/default" "${volumes}" "${containers}"
  : >"${project_directory}/tools/uv/Dockerfile"
  : >"${project_directory}/tools/rclone/Dockerfile"
  : >"${calls}"
  set_profile default
  profile_image_id=sha256:base
  profile_generation=1
}

# Add the volume NAME with the labels of TOOL, PROFILE and GENERATION,
# built from the profile image volume_base, by default sha256:base,
# used by the containers given after them.
add_volume() {
  declare name="$1" tool="$2" profile="$3" generation="$4"
  shift 4
  printf '%s\n' "tool=${tool}" "profile=${profile}" \
    "generation=${generation}" "build=earlier" \
    "base-image=${volume_base:-sha256:base}" "profile-generation=1" \
    >"${volumes}/${name}"
  printf '%s\n' "$@" >"${volumes}/${name}.users"
}

# Print the value of the label KEY of the volume NAME.
volume_label() {
  declare name="$1" key="$2"
  sed -n "s/^${key}=//p" -- "${volumes}/${name}"
}

# A fake docker for the commands the tool functions use,
# recording builds, creations and removals in calls.
# The built tool image gives the version in image_version, if set,
# and a tool's latest-version prints latest_output, failing when unset.
docker() {
  declare argument name tool='' profile='' version='' base='' quiet=''
  declare generation='' format='' spec labels
  case "$1 $2" in
  'volume ls')
    for argument in "$@"; do
      case "${argument}" in
      --quiet) quiet=1 ;;
      label=dockered-claude.tool=*) tool="${argument##*=}" ;;
      label=dockered-claude.profile=*) profile="${argument##*=}" ;;
      label=dockered-claude.version=*) version="${argument##*=}" ;;
      label=dockered-claude.base-image=*) base="${argument##*=}" ;;
      label=dockered-claude.generation=*) generation="${argument##*=}" ;;
      '{{'*) format="${argument}" ;;
      esac
    done
    for name in "${volumes}"/*; do
      [[ -e "${name}" && "${name}" != *.users ]] || continue
      [[ "$(volume_label "${name##*/}" tool)" == "${tool}" ]] || continue
      [[ "$(volume_label "${name##*/}" profile)" == "${profile}" ]] || continue
      [[ -z "${version}" ||
        "$(volume_label "${name##*/}" version)" == "${version}" ]] || continue
      [[ -z "${base}" ||
        "$(volume_label "${name##*/}" base-image)" == "${base}" ]] || continue
      [[ -z "${generation}" ||
        "$(volume_label "${name##*/}" generation)" == "${generation}" ]] ||
        continue
      if [[ "${format}" == *profile-generation* && "${format}" != */* ]]; then
        volume_label "${name##*/}" profile-generation
      elif [[ -n "${quiet}" ]]; then
        printf '%s\n' "${name##*/}"
      else
        printf '%s/%s/%s\n' "$(volume_label "${name##*/}" generation)" \
          "$(volume_label "${name##*/}" base-image)" "${name##*/}"
      fi
    done
    ;;
  'create sha256:tool') printf 'reader\n' ;;
  'run --cap-drop')
    printf 'run %s\n' "$(cat)" >>"${calls}"
    [[ -n "${latest_output+defined}" ]] || return 1
    printf '%s\n' "${latest_output}"
    ;;
  'cp reader:'*)
    [[ -n "${image_version:-}" ]] || return 1
    mkdir -p -- "${temporary_directory}/image"
    printf '%s\n' "${image_version}" >"${temporary_directory}/image/version"
    tar -cf - -C "${temporary_directory}/image" version
    ;;
  'volume inspect')
    volume_label "${!#}" build
    ;;
  'ps --all')
    name="${!#}"
    name="${name#volume=}"
    [[ ! -s "${volumes}/${name}.users" ]] || cat -- "${volumes}/${name}.users"
    ;;
  'build --build-arg')
    printf 'build %s\n' "$3" >>"${calls}"
    for argument in "$@"; do
      [[ -z "${name:-}" ]] || {
        printf 'sha256:tool\n' >"${argument}"
        break
      }
      [[ "${argument}" != --iidfile ]] || name=1
    done
    ;;
  'create --mount')
    spec="$3"
    name="${spec#type=volume,src=}"
    name="${name%%,*}"
    printf 'create %s\n' "${name}" >>"${calls}"
    [[ ! -e "${containers}/$5" ]] || return 1
    : >"${containers}/$5"
    if [[ ! -e "${volumes}/${name}" ]]; then
      labels="${spec#*,volume-label=}"
      printf '%s\n' "${labels//,volume-label=/$'\n'}" |
        sed 's/^dockered-claude\.//' >"${volumes}/${name}"
    fi
    ;;
  'rm '*) rm -f -- "${containers}/$2" ;;
  'image rm') printf 'image rm %s\n' "$3" >>"${calls}" ;;
  *) return 1 ;;
  esac
}

test_finding_orders_generations_numerically() {
  reset_tools
  add_volume dockered-claude-tool-default-uv-10 uv default 10
  add_volume dockered-claude-tool-default-uv-9 uv default 9
  add_volume dockered-claude-tool-minimal-uv-11 uv minimal 11
  add_volume dockered-claude-tool-default-rclone-12 rclone default 12
  add_volume broken uv default x
  declare -a tool_volumes tool_generations
  capture find_tool_volumes uv
  assert_status 0
  assert_array tool_generations 9 10
  assert_array tool_volumes dockered-claude-tool-default-uv-9 \
    dockered-claude-tool-default-uv-10
}

test_building_makes_the_first_generation_with_its_labels() {
  reset_tools
  capture build_tool_volume uv refresh
  assert_status 0
  assert_file "${calls}" \
    $'build BASE_IMAGE=dockered-claude-default:latest\ncreate dockered-claude-tool-default-1-uv-1\nimage rm sha256:tool'
  assert_equal $'uv\ndefault\n1' "$(head -n 3 -- \
    "${volumes}/dockered-claude-tool-default-1-uv-1" | cut -d = -f 2)"
  assert_equal sha256:base \
    "$(volume_label dockered-claude-tool-default-1-uv-1 base-image)"
  assert_equal 1 \
    "$(volume_label dockered-claude-tool-default-1-uv-1 profile-generation)"
}

test_building_makes_the_next_generation_beside_one_in_use() {
  reset_tools
  add_volume dockered-claude-tool-default-uv-1 uv default 1 container
  add_volume dockered-claude-tool-default-uv-2 uv default 2 container
  capture build_tool_volume uv refresh
  assert_status 0
  assert_contains "$(<"${calls}")" 'create dockered-claude-tool-default-1-uv-3'
  [[ -e "${volumes}/dockered-claude-tool-default-uv-2" ]] ||
    fail 'expected the volume in use to stay'
}

test_building_refuses_a_volume_made_by_another_build() {
  reset_tools
  # Another build made generation 1 between listing and filling.
  # shellcheck disable=SC2329 # Called by build_tool_volume.
  find_tool_volumes() {
    tool_volumes=()
    tool_generations=()
    tool_newest_generation=0
  }
  add_volume dockered-claude-tool-default-1-uv-1 uv default 1
  capture build_tool_volume uv
  assert_status 1
  assert_contains "${errors}" 'dockered-claude-tool-default-1-uv-1 existed already'
  assert_contains "$(<"${calls}")" 'image rm sha256:tool'
}

test_building_refuses_a_fill_in_progress() {
  reset_tools
  : >"${containers}/dockered-claude-tool-default-1-uv-1-fill"
  capture build_tool_volume uv
  assert_status 1
  assert_contains "${errors}" 'docker rm dockered-claude-tool-default-1-uv-1-fill'
  assert_contains "$(<"${calls}")" 'image rm sha256:tool'
}

test_running_mounts_the_newest_and_builds_missing_tools() {
  reset_tools
  add_volume dockered-claude-tool-default-uv-1 uv default 1
  add_volume dockered-claude-tool-default-uv-2 uv default 2
  mounted_tools=(uv rclone uv)
  capture find_tool_volume_names
  assert_status 0
  assert_equal dockered-claude-tool-default-uv-2 "${tool_volume_names[uv]}"
  assert_equal dockered-claude-tool-default-1-rclone-1 \
    "${tool_volume_names[rclone]}"
  assert_contains "${errors}" "building tool 'rclone' for profile 'default'"
}

test_running_warns_only_about_older_volumes_no_container_uses() {
  reset_tools
  add_volume dockered-claude-tool-default-uv-1 uv default 1
  add_volume dockered-claude-tool-default-uv-2 uv default 2 container
  add_volume dockered-claude-tool-default-uv-3 uv default 3
  add_volume dockered-claude-tool-default-rclone-1 rclone default 1
  mounted_tools=(uv rclone)
  tool_volume_names=([uv]=dockered-claude-tool-default-uv-3
    [rclone]=dockered-claude-tool-default-rclone-1)
  capture warn_unused_tool_volumes
  assert_status 0
  assert_contains "${errors}" \
    'docker volume rm dockered-claude-tool-default-uv-1'
  [[ "${errors}" != *uv-2* && "${errors}" != *uv-3* && "${errors}" != *rclone* ]] ||
    fail "expected only uv-1: ${errors}"
}

test_running_without_older_volumes_warns_nothing() {
  reset_tools
  add_volume dockered-claude-tool-default-uv-1 uv default 1
  mounted_tools=(uv rclone)
  tool_volume_names=([uv]=dockered-claude-tool-default-uv-1)
  capture warn_unused_tool_volumes
  assert_status 0
  assert_equal '' "${errors}"
}

test_building_names_a_volume_by_the_version_the_tool_gives() {
  reset_tools
  add_volume dockered-claude-tool-default-uv-1 uv default 1
  image_version=2.1.328
  capture build_tool_volume uv refresh
  assert_status 0
  assert_contains "$(<"${calls}")" 'create dockered-claude-tool-default-1-uv-2.1.328'
  assert_equal 2 "$(volume_label dockered-claude-tool-default-1-uv-2.1.328 generation)"
  assert_equal 2.1.328 "$(volume_label dockered-claude-tool-default-1-uv-2.1.328 version)"
}

test_building_keeps_a_version_built_already() {
  reset_tools
  add_volume dockered-claude-tool-default-uv-2.1.328 uv default 1
  printf '%s\n' version=2.1.328 >>"${volumes}/dockered-claude-tool-default-uv-2.1.328"
  image_version=2.1.328
  capture build_tool_volume uv refresh
  assert_status 0
  assert_contains "${errors}" \
    "tool 'uv' 2.1.328 for profile 'default' is built already in dockered-claude-tool-default-uv-2.1.328"
  [[ "$(<"${calls}")" != *'create dockered-claude'* ]] ||
    fail 'expected no new volume'
  assert_contains "$(<"${calls}")" 'image rm sha256:tool'
}

test_building_refuses_an_invalid_version() {
  reset_tools
  image_version='1.0 beta'
  capture build_tool_volume uv
  assert_status 1
  assert_contains "${errors}" "invalid version of tool 'uv': '1.0 beta'"
  assert_contains "$(<"${calls}")" 'image rm sha256:tool'
}

test_building_skips_a_latest_version_built_already() {
  reset_tools
  add_volume dockered-claude-tool-default-uv-2.1.328 uv default 1
  printf '%s\n' version=2.1.328 >>"${volumes}/dockered-claude-tool-default-uv-2.1.328"
  printf '%s\n' 'echo 2.1.328' >"${project_directory}/tools/uv/latest-version"
  latest_output=2.1.328
  capture build_tool_volume uv refresh
  assert_status 0
  assert_contains "${errors}" \
    "tool 'uv' 2.1.328 for profile 'default' is built already"
  assert_file "${calls}" 'run echo 2.1.328'
}

test_building_goes_ahead_for_a_new_latest_version() {
  reset_tools
  add_volume dockered-claude-tool-default-uv-2.1.328 uv default 1
  printf '%s\n' version=2.1.328 >>"${volumes}/dockered-claude-tool-default-uv-2.1.328"
  : >"${project_directory}/tools/uv/latest-version"
  latest_output=2.1.329
  image_version=2.1.329
  capture build_tool_volume uv refresh
  assert_status 0
  assert_contains "$(<"${calls}")" 'create dockered-claude-tool-default-1-uv-2.1.329'
}

test_building_goes_ahead_when_latest_version_fails() {
  reset_tools
  : >"${project_directory}/tools/uv/latest-version"
  capture build_tool_volume uv
  assert_status 0
  assert_contains "${errors}" "cannot tell the latest version of tool 'uv'; building it"
  assert_contains "$(<"${calls}")" 'create dockered-claude-tool-default-1-uv-1'
}

test_building_goes_ahead_when_latest_version_is_invalid() {
  reset_tools
  : >"${project_directory}/tools/uv/latest-version"
  latest_output='<html>'
  capture build_tool_volume uv
  assert_status 0
  assert_contains "${errors}" "invalid latest version of tool 'uv': '<html>'"
  assert_contains "$(<"${calls}")" 'create dockered-claude-tool-default-1-uv-1'
}

test_finding_takes_only_volumes_of_the_profile_image() {
  reset_tools
  add_volume dockered-claude-tool-default-1-uv-1 uv default 1
  volume_base=sha256:other add_volume dockered-claude-tool-default-2-uv-2 \
    uv default 2
  printf '%s\n' tool=uv profile=default generation=3 \
    >"${volumes}/dockered-claude-tool-default-uv-3"
  declare -a tool_volumes tool_generations
  capture find_tool_volumes uv
  assert_status 0
  assert_array tool_volumes dockered-claude-tool-default-1-uv-1
  assert_equal 3 "${tool_newest_generation}"
}

test_building_after_a_profile_build_continues_the_generations() {
  reset_tools
  volume_base=sha256:old add_volume dockered-claude-tool-default-1-uv-4 \
    uv default 4
  profile_image_id=sha256:new
  profile_generation=2
  capture build_tool_volume uv refresh
  assert_status 0
  assert_contains "$(<"${calls}")" 'create dockered-claude-tool-default-2-uv-5'
  assert_equal sha256:new \
    "$(volume_label dockered-claude-tool-default-2-uv-5 base-image)"
}

test_running_builds_a_tool_built_only_from_another_image() {
  reset_tools
  volume_base=sha256:old add_volume dockered-claude-tool-default-1-uv-1 \
    uv default 1
  mounted_tools=(uv)
  capture find_tool_volume_names
  assert_status 0
  assert_equal dockered-claude-tool-default-1-uv-2 "${tool_volume_names[uv]}"
}

test_running_mounts_a_pinned_generation() {
  reset_tools
  add_volume dockered-claude-tool-default-1-uv-1 uv default 1
  add_volume dockered-claude-tool-default-1-uv-2 uv default 2
  mounted_tools=(uv)
  tool_pins=([uv]=1)
  capture find_tool_volume_names
  assert_status 0
  assert_equal dockered-claude-tool-default-1-uv-1 "${tool_volume_names[uv]}"
}

test_running_refuses_a_pin_built_from_another_profile_image() {
  reset_tools
  volume_base=sha256:old add_volume dockered-claude-tool-default-1-uv-1 \
    uv default 1
  add_volume dockered-claude-tool-default-2-uv-2 uv default 2
  profile_generation=2
  mounted_tools=(uv)
  tool_pins=([uv]=1)
  capture find_tool_volume_names
  assert_status 1
  assert_contains "${errors}" \
    "was built from generation 1 of profile 'default', not from the one latest marks (2)"
  assert_contains "${errors}" 'profile use default 1'
}

test_running_refuses_a_pin_that_is_gone() {
  reset_tools
  add_volume dockered-claude-tool-default-1-uv-2 uv default 2
  mounted_tools=(uv)
  tool_pins=([uv]=1)
  capture find_tool_volume_names
  assert_status 1
  assert_contains "${errors}" 'no longer exists'
  assert_file "${calls}" ''
}

test_running_warns_about_the_newest_when_an_older_one_is_pinned() {
  reset_tools
  add_volume dockered-claude-tool-default-1-uv-1 uv default 1
  add_volume dockered-claude-tool-default-1-uv-2 uv default 2
  mounted_tools=(uv)
  tool_volume_names=([uv]=dockered-claude-tool-default-1-uv-1)
  capture warn_unused_tool_volumes
  assert_status 0
  assert_contains "${errors}" 'docker volume rm dockered-claude-tool-default-1-uv-2'
  [[ "${errors}" != *uv-1* ]] || fail "expected only uv-2: ${errors}"
}
