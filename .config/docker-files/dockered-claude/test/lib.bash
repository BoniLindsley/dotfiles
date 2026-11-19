# Helpers for the launcher's tests, without a test framework.
# test/run sources this file in a fresh bash for each test file
# and calls run_tests,
# which runs each test_ function of that file in its own subshell.
# Tests may therefore set globals freely:
# nothing they set outlives their subshell.

repository="$(cd -- "${BASH_SOURCE[0]%/*}/.." && pwd -P)" || return

# Source file and run each of its test_ functions in its own subshell,
# printing "ok" or "not ok" with the test's name,
# followed by what a failed test printed,
# then a count, and fail if any test failed.
run_tests() {
  declare file="$1" name test log
  declare -i passed=0 failed=0
  declare -a tests=()

  name="${file#"${repository}/"}"
  # shellcheck source=/dev/null
  source -- "${file}" || return
  mapfile -t tests < <(compgen -A function test_)
  if ((${#tests[@]} == 0)); then
    printf '# %s: no tests\n' "${name}"
    return 1
  fi

  log="$(mktemp)" || return
  for test in "${tests[@]}"; do
    # Errexit is ignored inside anything run from if, || or &&,
    # even in a subshell that sets it again,
    # so the subshell runs as a command of its own
    # and its status is read afterwards.
    (
      set -eEuo pipefail
      start_test
      "${test}"
    ) >"${log}" 2>&1
    # shellcheck disable=SC2181 # Read apart from the subshell, as above.
    if (($? == 0)); then
      printf 'ok - %s: %s\n' "${name}" "${test}"
      passed+=1
    else
      printf 'not ok - %s: %s\n' "${name}" "${test}"
      sed 's/^/# /' -- "${log}"
      failed+=1
    fi
  done
  rm -f -- "${log}"

  printf '# %s: %d passed, %d failed\n' "${name}" "${passed}" "${failed}"
  ((failed == 0))
}

# Set temporary_directory to a new directory,
# removed when the test's subshell exits,
# and report a command that fails the test through errexit.
start_test() {
  temporary_directory="$(mktemp -d)"
  trap 'rm -rf -- "${temporary_directory}"' EXIT
  # shellcheck disable=SC2154 # BASH_COMMAND is set by bash.
  trap 'printf "command failed with status %d: %s\nat %s:%s\n" \
    "$?" "${BASH_COMMAND}" "${BASH_SOURCE[0]#"${repository}/"}" "${LINENO}" >&2' ERR
}

# The launcher, which test files source themselves, without running main:
# sourced inside a function,
# its top-level declarations would be local to that function.
launcher="${repository}/bin/dockered-claude"

# Set the paths that the launcher's main would declare.
# shellcheck disable=SC2034 # Read by the launcher's functions.
set_launcher_paths() {
  script_name="${launcher##*/}"
  project_directory="${repository}"
}

# Fail the current test, printing each argument on a line,
# then where in the test it failed.
# Each test runs in its own subshell,
# so leaving that subshell is how a failed assertion stops the test.
fail() {
  declare -i index
  printf '%s\n' "$@" >&2
  for index in "${!FUNCNAME[@]}"; do
    if [[ "${FUNCNAME[index]}" == test_* ]]; then
      printf 'at %s:%s\n' \
        "${BASH_SOURCE[index]#"${repository}/"}" "${BASH_LINENO[index - 1]}" >&2
      break
    fi
  done
  exit 1
}

# Run a command in this shell, so that the variables it sets stay set.
# Errexit is ignored while it runs,
# as in the launcher, whose main calls its functions with || return.
# Set output and errors to what it printed,
# without trailing newlines,
# and status to its exit status.
# shellcheck disable=SC2034 # Read by the tests.
capture() {
  declare capture_file="${temporary_directory}/capture"
  if "$@" >"${capture_file}.out" 2>"${capture_file}.err"; then
    status=0
  else
    status=$?
  fi
  output="$(<"${capture_file}.out")"
  errors="$(<"${capture_file}.err")"
}

assert_equal() {
  declare expected="$1" actual="$2"
  [[ "${actual}" == "${expected}" ]] && return
  fail "expected: $(printf '%q' "${expected}")" \
    "actual:   $(printf '%q' "${actual}")"
}

# Assert that text contains fragment.
assert_contains() {
  declare text="$1" fragment="$2"
  [[ "${text}" == *"${fragment}"* ]] && return
  fail "expected to contain: $(printf '%q' "${fragment}")" \
    "actual: $(printf '%q' "${text}")"
}

# Assert that the last command captured exited with expected,
# showing what it printed to standard error if not.
assert_status() {
  declare expected="$1"
  ((status == expected)) && return
  fail "expected status ${expected}, got ${status}" \
    "errors: $(printf '%q' "${errors}")"
}

# Assert that the array named name holds the remaining arguments.
assert_array() {
  declare -n assert_array_actual="$1"
  shift
  declare expected actual
  expected="$(printf '%q ' "$@")"
  actual="$(printf '%q ' "${assert_array_actual[@]}")"
  [[ "${actual}" == "${expected}" ]] && return
  fail "expected: (${expected% })" "actual:   (${actual% })"
}

# Assert that the file at path holds expected,
# ignoring trailing newlines.
assert_file() {
  declare path="$1" expected="$2"
  [[ -f "${path}" ]] || fail "expected a file: ${path}"
  assert_equal "${expected}" "$(<"${path}")"
}
