#!/usr/bin/env bash

main() {
  local hostname='www.google.com'
  local port='80'

  # Connect to given port.
  # Fails if hostname unknown or connection refused.
  # There is also `/dev/udp`.
  exec 3<>"/dev/tcp/${hostname}/${port}" || return

  # Write to socket.
  echo -e "GET / HTTP/1.0\r\nHost: ${hostname}\r\n\r" >&3

  # Read from socket.
  cat <&3

  # Close connection.
  exec 3<&-
}

main "$@"
