# Tests of what each command does, with Docker and builds replaced.
# test/run sources test/lib.bash first,
# which sets launcher and temporary_directory,
# and whose capture sets output, errors and status.
# shellcheck disable=SC2154

# shellcheck source=../../bin/dockered-claude
source -- "${launcher}" || return

# Declare, as globals of the test's subshell,
# the arrays that the launcher's main declares,
# with the launcher's directory and HOME in temporary_directory,
# and calls set to a file where replaced functions record their calls.
reset_commands() {
  set_launcher_paths
  declare -gA kwargs=()
  declare -ga args=() tools=() packages=() mounts=()
  project_directory="${temporary_directory}/launcher"
  HOME="${temporary_directory}/home"
  calls="${temporary_directory}/calls"
  mkdir -p -- "${project_directory}/profiles/default" "${HOME}"
  : >"${project_directory}/profiles/default/Dockerfile"
  : >"${calls}"
  cd -- "${HOME}" || return
}

# Record a call to the function that calls this, with its arguments.
record_call() {
  printf '%s\n' "${FUNCNAME[1]}${*:+ $*}" >>"${calls}"
}

# A fake docker for profile images,
# with the tags of each repository in fake_images, by repository,
# as lines of "TAG ID AGE".
# image ls of a repository prints them;
# build writes fake_build_id to the file of --iidfile;
# tag moves or adds a tag in fake_images.
# Builds and tags are recorded in calls, the --iidfile file left out.
fake_profile_docker() {
  declare repository tag line kept=''
  case "$1" in
  image)
    [[ "$2" == ls ]] || return 1
    printf '%s' "${fake_images[${!#}]:-}"
    ;;
  build)
    [[ "$2" == --iidfile ]] || return 1
    printf '%s' "${fake_build_id}" >"$3"
    printf '%s\n' "docker build ${*:4}" >>"${calls}"
    ;;
  tag)
    printf '%s\n' "docker $*" >>"${calls}"
    repository="${3%:*}"
    tag="${3##*:}"
    while IFS= read -r line; do
      [[ -n "${line}" && "${line%% *}" != "${tag}" ]] || continue
      kept+="${line}"$'\n'
    done <<<"${fake_images[${repository}]:-}"
    fake_images[${repository}]="${kept}${tag} $2 now"$'\n'
    ;;
  *) return 1 ;;
  esac
}

# Declare the state for build_image and ensure_image
# with the profile default and the fake docker for profile images.
reset_profile_images() {
  reset_commands
  set_profile default
  declare -gA fake_images=()
  fake_build_id=sha256:new
  # shellcheck disable=SC2329 # Called by the functions tested.
  docker() { fake_profile_docker "$@"; }
}

test_building_a_profile_tags_the_first_generation_and_latest() {
  reset_profile_images
  capture build_image
  assert_status 0
  assert_file "${calls}" \
    "docker build --label dockered-claude.profile=default --pull ${project_directory}/profiles/default
docker tag sha256:new dockered-claude-default:1
docker tag sha256:new dockered-claude-default:latest"
  assert_contains "${errors}" "built generation 1 of profile 'default'"
}

test_building_a_profile_without_the_cache_passes_no_cache() {
  reset_profile_images
  kwargs[no_cache]=1
  capture build_image
  assert_status 0
  assert_contains "$(<"${calls}")" \
    "docker build --label dockered-claude.profile=default --no-cache --pull "
}

test_building_a_profile_adds_a_generation_after_the_newest() {
  reset_profile_images
  fake_images["dockered-claude-default"]=$'1 sha256:a 2 weeks ago\n3 sha256:c 2 days ago\nlatest sha256:a 2 weeks ago\n'
  capture build_image
  assert_status 0
  assert_contains "$(<"${calls}")" \
    $'docker tag sha256:new dockered-claude-default:4\ndocker tag sha256:new dockered-claude-default:latest'
}

test_building_a_profile_as_built_already_marks_that_generation() {
  reset_profile_images
  fake_images["dockered-claude-default"]=$'1 sha256:a 2 weeks ago\n2 sha256:b 2 days ago\nlatest sha256:b 2 days ago\n'
  fake_build_id=sha256:a
  capture build_image
  assert_status 0
  assert_equal 'docker tag sha256:a dockered-claude-default:latest' \
    "$(grep '^docker tag' "${calls}")"
  assert_contains "${errors}" 'is generation 1, built already'
}

test_building_a_profile_keeps_an_earlier_latest_as_a_generation() {
  reset_profile_images
  fake_images["dockered-claude-default"]=$'latest sha256:old 3 months ago\n'
  capture build_image
  assert_status 0
  assert_equal $'docker tag sha256:old dockered-claude-default:1\ndocker tag sha256:new dockered-claude-default:2\ndocker tag sha256:new dockered-claude-default:latest' \
    "$(grep '^docker tag' "${calls}")"
}

test_profile_use_marks_a_generation_latest() {
  reset_profile_images
  fake_images["dockered-claude-default"]=$'1 sha256:a 2 weeks ago\n2 sha256:b 2 days ago\nlatest sha256:b 2 days ago\n'
  parse_arguments profile use default 1
  capture run
  assert_status 0
  assert_file "${calls}" 'docker tag sha256:a dockered-claude-default:latest'
}

test_profile_use_refuses_a_missing_generation() {
  reset_profile_images
  fake_images["dockered-claude-default"]=$'1 sha256:a 2 weeks ago\nlatest sha256:a 2 weeks ago\n'
  parse_arguments profile use default 2
  capture run
  assert_status 1
  assert_contains "${errors}" "profile 'default' has no generation 2"
  assert_file "${calls}" ''
}

test_profile_revert_marks_the_generation_before_latest() {
  reset_profile_images
  fake_images["dockered-claude-default"]=$'1 sha256:a 3 weeks ago\n3 sha256:c 2 weeks ago\n4 sha256:d 2 days ago\nlatest sha256:c 2 weeks ago\n'
  parse_arguments profile revert default
  capture run
  assert_status 0
  assert_file "${calls}" 'docker tag sha256:a dockered-claude-default:latest'
  assert_contains "${errors}" 'marked generation 1 of profile'
}

test_profile_revert_fails_at_the_first_generation() {
  reset_profile_images
  fake_images["dockered-claude-default"]=$'1 sha256:a 3 weeks ago\nlatest sha256:a 3 weeks ago\n'
  parse_arguments profile revert default
  capture run
  assert_status 1
  assert_contains "${errors}" "profile 'default' has no generation before 1"
}

test_ensuring_an_image_adopts_an_earlier_latest_without_building() {
  reset_profile_images
  fake_images["dockered-claude-default"]=$'latest sha256:old 3 months ago\n'
  capture ensure_image
  assert_status 0
  assert_file "${calls}" 'docker tag sha256:old dockered-claude-default:1'
}

test_ensuring_an_image_leaves_a_marked_generation_alone() {
  reset_profile_images
  fake_images["dockered-claude-default"]=$'1 sha256:a 2 weeks ago\nlatest sha256:a 2 weeks ago\n'
  capture ensure_image
  assert_status 0
  assert_file "${calls}" ''
}

test_ensuring_an_image_refuses_generations_without_latest() {
  reset_profile_images
  fake_images["dockered-claude-default"]=$'1 sha256:a 2 weeks ago\n'
  capture ensure_image
  assert_status 1
  assert_contains "${errors}" "no generation of profile 'default' is marked latest"
  assert_file "${calls}" ''
}

test_ensuring_an_image_builds_a_missing_one() {
  reset_profile_images
  capture ensure_image
  assert_status 0
  assert_contains "$(<"${calls}")" 'docker tag sha256:new dockered-claude-default:latest'
}

test_tool_list_shows_which_tools_are_built() {
  reset_commands
  mkdir -p -- "${project_directory}"/tools/{built,missing,old,empty}
  : >"${project_directory}/tools/built/Dockerfile"
  : >"${project_directory}/tools/missing/Dockerfile"
  : >"${project_directory}/tools/old/Dockerfile"
  # shellcheck disable=SC2329 # Called by list_tools.
  docker() {
    case "$*" in
    'image ls '*) printf '%s\n' 'latest sha256:base now' '1 sha256:base now' ;;
    *'label=dockered-claude.tool=built '*'label=dockered-claude.profile=default '*)
      printf '%s\n' '1/sha256:old/1/dockered-claude-tool-default-1-built-1' \
        '3/sha256:base/2/dockered-claude-tool-default-2-built-3' \
        '2/sha256:base/2/dockered-claude-tool-default-2-built-2'
      ;;
    *'label=dockered-claude.tool=old '*)
      printf '%s\n' '1///dockered-claude-tool-default-old-1'
      ;;
    esac
  }
  parse_arguments tool list
  capture run
  assert_status 0
  assert_equal 'built
  3, built from generation 2 of the profile (used unless pinned)
  2, built from generation 2 of the profile
  1, built from generation 1 of the profile
missing (not built)
old
  1, built before tool volumes were tied to profile images' "${output}"
}

test_tool_build_builds_each_tool_without_the_cache() {
  reset_commands
  # shellcheck disable=SC2329 # Called by run.
  ensure_image() { record_call; }
  # shellcheck disable=SC2329 # Called by run.
  read_profile_image() { :; }
  # shellcheck disable=SC2329 # Called by run.
  build_tool_volume() { record_call "$@"; }
  parse_arguments tool build vcpkg uv
  capture run
  assert_status 0
  assert_file "${calls}" $'ensure_image\nbuild_tool_volume vcpkg refresh\nbuild_tool_volume uv refresh'
}

test_build_rebuilds_the_image_and_the_saved_packages() {
  reset_commands
  mkdir -p -- "${HOME}/project/.meta/dockered-claude"
  printf '%s\n' 'packages = gdb libssl-dev' \
    >"${HOME}/project/.meta/dockered-claude/config"
  cd -- "${HOME}/project" || return
  # shellcheck disable=SC2329 # Called by build_images.
  build_image() { record_call; }
  # shellcheck disable=SC2329 # Called by build_images.
  ensure_packages_image() { record_call "${packages[@]}"; }
  parse_arguments build
  capture run
  assert_status 0
  assert_file "${calls}" $'build_image\nensure_packages_image gdb libssl-dev'
}

# Answer the docker calls of ensure_packages_image
# as if the packages image was built from the current base image.
docker_with_current_packages_image() {
  case "$*" in
  'image inspect --format {{.Id}} '*) printf 'sha256:base\n' ;;
  'image ls '*) printf 'latest sha256:base now\n1 sha256:base now\n' ;;
  'image inspect --format {{index .Config.Labels '*) printf 'sha256:base\n' ;;
  build\ *) printf 'docker build\n' >>"${calls}" ;;
  *) return 1 ;;
  esac
}

test_running_keeps_a_current_packages_image() {
  reset_commands
  set_profile default
  packages=(gdb)
  kwargs[command]=run
  # shellcheck disable=SC2329 # Called by ensure_packages_image.
  docker() { docker_with_current_packages_image "$@"; }
  capture ensure_packages_image
  assert_status 0
  assert_file "${calls}" ''
  assert_contains "${container_image}" 'dockered-claude-default:packages-'
  [[ "${container_image}" == *-1 ]] ||
    fail "expected the generation in the tag: ${container_image}"
}

test_build_rebuilds_a_current_packages_image() {
  reset_commands
  set_profile default
  packages=(gdb)
  kwargs[command]=build
  # shellcheck disable=SC2329 # Called by ensure_packages_image.
  docker() { docker_with_current_packages_image "$@"; }
  capture ensure_packages_image
  assert_status 0
  assert_file "${calls}" 'docker build'
}

test_profile_list_shows_the_generations_of_each_profile() {
  reset_commands
  mkdir -p -- "${project_directory}"/profiles/{minimal,old,empty}
  : >"${project_directory}/profiles/minimal/Dockerfile"
  : >"${project_directory}/profiles/old/Dockerfile"
  declare -gA fake_images=(
    ["dockered-claude-default"]=$'1 sha256:a 2 weeks ago\n2 sha256:b 2 days ago\nlatest sha256:a 2 weeks ago\n'
    ["dockered-claude-old"]=$'latest sha256:o 3 months ago\n'
  )
  # shellcheck disable=SC2329 # Called by list_profiles.
  docker() { fake_profile_docker "$@"; }
  parse_arguments profile list
  capture run
  assert_status 0
  assert_equal 'default
  2, built 2 days ago
  1, built 2 weeks ago (latest)
minimal (not built)
old
  latest, from an earlier version of the launcher' "${output}"
}

test_profile_build_builds_each_profile() {
  reset_commands
  mkdir -p -- "${project_directory}/profiles/minimal"
  : >"${project_directory}/profiles/minimal/Dockerfile"
  # shellcheck disable=SC2329 # Called by run.
  build_image() { record_call "${profile}" "${image}"; }
  parse_arguments profile build minimal default
  capture run
  assert_status 0
  assert_file "${calls}" \
    $'build_image minimal dockered-claude-minimal:latest\nbuild_image default dockered-claude-default:latest'
}

test_profile_build_refuses_a_missing_profile() {
  reset_commands
  # shellcheck disable=SC2329 # Called by run.
  build_image() { record_call "${profile}"; }
  parse_arguments profile build default missing
  capture run
  assert_status 1
  assert_contains "${errors}" "no profile 'missing'"
  assert_file "${calls}" 'build_image default'
}

test_build_builds_the_saved_profile() {
  reset_commands
  mkdir -p -- "${project_directory}/profiles/minimal" \
    "${HOME}/project/.meta/dockered-claude"
  : >"${project_directory}/profiles/minimal/Dockerfile"
  printf '%s\n' 'profile = minimal' \
    >"${HOME}/project/.meta/dockered-claude/config"
  cd -- "${HOME}/project" || return
  declare -gA fake_images=()
  fake_build_id=sha256:new
  # shellcheck disable=SC2329 # Called by build_images.
  docker() { fake_profile_docker "$@"; }
  parse_arguments build
  capture run
  assert_status 0
  assert_contains "$(<"${calls}")" \
    "docker build --label dockered-claude.profile=minimal --pull ${project_directory}/profiles/minimal"
  assert_contains "$(<"${calls}")" \
    'docker tag sha256:new dockered-claude-minimal:latest'
}

test_tool_build_uses_the_given_profile() {
  reset_commands
  mkdir -p -- "${project_directory}/profiles/minimal"
  : >"${project_directory}/profiles/minimal/Dockerfile"
  # shellcheck disable=SC2329 # Called by run.
  ensure_image() { record_call "${image}"; }
  # shellcheck disable=SC2329 # Called by run.
  read_profile_image() { :; }
  # shellcheck disable=SC2329 # Called by run.
  build_tool_volume() { record_call "$@"; }
  parse_arguments tool build --profile minimal uv
  capture run
  assert_status 0
  assert_file "${calls}" \
    $'ensure_image dockered-claude-minimal:latest\nbuild_tool_volume uv refresh'
}

test_tool_build_uses_the_profile_of_the_environment() {
  reset_commands
  mkdir -p -- "${project_directory}/profiles/minimal"
  : >"${project_directory}/profiles/minimal/Dockerfile"
  DOCKERED_CLAUDE_PROFILE=minimal
  # shellcheck disable=SC2329 # Called by run.
  ensure_image() { record_call "${image}"; }
  # shellcheck disable=SC2329 # Called by run.
  read_profile_image() { :; }
  # shellcheck disable=SC2329 # Called by run.
  build_tool_volume() { record_call "$@"; }
  parse_arguments tool build uv
  capture run
  assert_status 0
  assert_file "${calls}" \
    $'ensure_image dockered-claude-minimal:latest\nbuild_tool_volume uv refresh'
}

test_packages_use_the_profile_dockerfile_when_it_has_one() {
  reset_commands
  set_profile default
  packages=(gdb)
  kwargs[command]=build
  : >"${project_directory}/profiles/default/Dockerfile.packages"
  # shellcheck disable=SC2329 # Called by ensure_packages_image.
  docker() {
    case "$*" in
    'image inspect --format {{.Id}} '*) printf 'sha256:base\n' ;;
    'image ls '*) printf 'latest sha256:base now\n1 sha256:base now\n' ;;
    build\ *) printf '%s\n' "$*" >>"${calls}" ;;
    *) return 1 ;;
    esac
  }
  capture ensure_packages_image
  assert_status 0
  assert_contains "$(<"${calls}")" \
    "--file ${project_directory}/profiles/default/Dockerfile.packages --label dockered-claude.profile=default"
  assert_contains "$(<"${calls}")" " ${project_directory}/profiles/default"
}

test_packages_use_the_launcher_dockerfile_otherwise() {
  reset_commands
  set_profile default
  packages=(gdb)
  kwargs[command]=build
  # shellcheck disable=SC2329 # Called by ensure_packages_image.
  docker() {
    case "$*" in
    'image inspect --format {{.Id}} '*) printf 'sha256:base\n' ;;
    'image ls '*) printf 'latest sha256:base now\n1 sha256:base now\n' ;;
    build\ *) printf '%s\n' "$*" >>"${calls}" ;;
    *) return 1 ;;
    esac
  }
  capture ensure_packages_image
  assert_status 0
  assert_contains "$(<"${calls}")" "--file ${project_directory}/Dockerfile.packages"
  assert_contains "$(<"${calls}")" "--tag dockered-claude-default:packages-"
}
