#!/usr/bin/env bash

__main() {
  # https://cmake.org/cmake/help/latest/envvar/CMAKE_EXPORT_COMPILE_COMMANDS.html#envvar:CMAKE_EXPORT_COMPILE_COMMANDS
  # Requires CMake 3.17.
  export CMAKE_EXPORT_COMPILE_COMMANDS=ON
}

__main "$@"
unset __main
