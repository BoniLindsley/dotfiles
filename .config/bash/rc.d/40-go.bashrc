#!/usr/bin/env bash

GOPATH="$HOME/.local/lib/go"
export GOPATH

prepend_to_path_if_exists "$GOPATH/bin"
