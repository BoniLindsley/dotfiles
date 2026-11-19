# End-to-end tests of the links of the run image, which need Docker
# and the image of profile default, or DOCKERED_CLAUDE_E2E_IMAGE.
# test/run --e2e sources test/lib.bash first,
# which sets launcher and temporary_directory.
# shellcheck disable=SC2154

# shellcheck source=../../bin/dockered-claude
source -- "${launcher}" || return

e2e_image="${DOCKERED_CLAUDE_E2E_IMAGE:-dockered-claude-default:latest}"

# Set base to a new directory in the home,
# since /tmp is reserved and links there would not be made,
# and remove it, and the images in e2e_images, when the test ends.
start_links_test() {
  set_launcher_paths
  declare -ga e2e_images=()
  base="$(mktemp -d "${HOME:?}/.dockered-claude-e2e.XXXXXX")"
  # shellcheck disable=SC2154 # e2e_images is expanded by the trap.
  trap 'rm -rf -- "${temporary_directory}" "${base}"
    ((${#e2e_images[@]} == 0)) ||
      docker image rm "${e2e_images[@]}" >/dev/null 2>&1 || :' EXIT
}

# Build an image from e2e_image with the directories given,
# each holding a file named image-file, and set container_image to its ID.
# A profile image may build as another user, who cannot write in /home.
build_base_image() {
  declare directory
  {
    printf 'FROM %s\nUSER root\n' "${e2e_image}"
    for directory in "$@"; do
      printf 'RUN mkdir -p %q && touch %q\n' \
        "${directory}" "${directory}/image-file"
    done
  } >"${temporary_directory}/Dockerfile"
  docker build --quiet --iidfile "${temporary_directory}/id" \
    --file "${temporary_directory}/Dockerfile" "${temporary_directory}" \
    >/dev/null
  container_image="$(<"${temporary_directory}/id")"
  e2e_images+=("${container_image}")
}

test_links_on_a_mount_path_are_made_and_the_images_files_kept() {
  start_links_test
  mkdir -p -- "${base}"/{1,b/3,d/5,f}
  ln -s -- "${base}/b" "${base}/1/2"
  ln -s -- "${base}/d" "${base}/b/3/4"
  ln -s -- "${base}/f" "${base}/d/5/6"
  : >"${base}/f/host-file"
  build_base_image "${base}/1" "${base}/b/3" "${base}/d/5"

  declare -a link_paths=() run_links=() mount_paths=("${base}/f") persisted_paths=()
  declare -A link_targets=() link_climbs=()
  declare traced_path run_image
  uid_host="$(id -u)"
  gid_host="$(id -g)"
  username="$(id -un)"
  groupname="$(id -gn)"
  home="${HOME}"
  workdir=/nonexistent
  profile=e2e
  trace_links "${base}/1/2/3/4/5/6"
  assert_equal "${base}/f" "${traced_path}"
  select_run_links
  build_run_image
  e2e_images+=("${run_image}")

  # shellcheck disable=SC2016 # Expanded by the container's sh.
  output="$(docker run --rm --entrypoint sh \
    --user "${uid_host}:${gid_host}" \
    --mount "type=bind,src=${base}/f,dst=${base}/f,readonly" \
    "${run_image}" -c '
      for link in 1/2 b/3/4 d/5/6; do readlink "$1/${link}"; done
      for file in 1 b/3 d/5; do ls "$1/${file}/image-file"; done
      ls "$1/1/2/3/4/5/6/host-file"' sh "${base}")"
  assert_equal "${base}/b
${base}/d
${base}/f
${base}/1/image-file
${base}/b/3/image-file
${base}/d/5/image-file
${base}/1/2/3/4/5/6/host-file" "${output}"
}
