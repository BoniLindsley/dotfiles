#!/usr/bin/env bash

# Overrides the default password storage directory.
#PASSWORD_STORE_DIR="$HOME/.password-store"
PASSWORD_STORE_DIR="$HOME/.config/password-store"
export PASSWORD_STORE_DIR

# Overrides the default gpg key identification set by init.
# Keys must not contain spaces and thus
# use of the hexadecimal key signature is recommended.
# Multiple keys may be specified separated by spaces.
#PASSWORD_STORE_KEY

# Additional options to be passed to all invocations of GPG.
#PASSWORD_STORE_GPG_OPTS

# Overrides the selection passed to xclip, by default clipboard.
# See xclip(1) for more info.
#PASSWORD_STORE_X_SELECTION=clipboard

# Specifies the number of seconds to wait before restoring the clipboard,
# by default 45 seconds.
#PASSWORD_STORE_CLIP_TIME=45

# Sets the umask of all files modified by pass, by default 077.
#PASSWORD_STORE_UMASK=077

# The default password length
# if the pass-length parameter to generate is unspecified.
#PASSWORD_STORE_GENERATED_LENGTH=25
PASSWORD_STORE_GENERATED_LENGTH=16
export PASSWORD_STORE_GENERATED_LENGTH

# The character set to be used in password generation for generate.
# This value is to be interpreted by tr. See tr(1) for more info.
#PASSWORD_STORE_CHARACTER_SET='[:graph:]'
PASSWORD_STORE_CHARACTER_SET='[:graph:]'
export PASSWORD_STORE_CHARACTER_SET

# The character set to be used
# in no-symbol password generation for generate,
# when --no-symbols, -n is specified.
# This value is to be interpreted by tr. See tr(1) for more info.
PASSWORD_STORE_CHARACTER_SET_NO_SYMBOLS='[:alnum:]-+_'
export PASSWORD_STORE_CHARACTER_SET_NO_SYMBOLS

# This environment variable must be set to "true"
# for extensions to be enabled.
#unset PASSWORD_STORE_ENABLE_EXTENSIONS
PASSWORD_STORE_ENABLE_EXTENSIONS=true
export PASSWORD_STORE_ENABLE_EXTENSIONS

# The location to look for executable extension files,
# by default PASSWORD_STORE_DIR/.extensions.
#PASSWORD_STORE_EXTENSIONS_DIR="$PASSWORD_STORE_DIR/.extensions"

# If this environment variable is set,
# then all .gpg-id files and non-system extension files
# must be signed using a detached signature using the GPG key specified
# by the full 40 character upper-case fingerprint in this variable.
# If multiple fingerprints are specified,
# each separated by a whitespace character,
# then signatures must match at least one.
# The init command will keep signatures of .gpg-id files up to date.
#unset PASSWORD_STORE_SIGNING_KEY
