#!/usr/bin/env bash

CARGO_HOME="$HOME/.local/lib/cargo"
export CARGO_HOME

RUSTUP_HOME="$HOME/.local/lib/rustup"
export RUSTUP_HOME

prepend_to_path_if_exists "$CARGO_HOME/bin"
