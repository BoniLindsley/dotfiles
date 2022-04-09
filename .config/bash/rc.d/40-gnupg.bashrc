#!/usr/bin/env bash

# Set the name of the home directory to DIR.
# If this option is not used, the home directory defaults to '~/.gnupg'.
# It is only recognized when given on the command line.
# It also overrides any home directory stated
# through the environment variable 'GNUPGHOME'
# or (on Windows systems) by means of the Registry entry
# HKCU\SOFTWARE\GNU\GNUPG:HOMEDIR.
#
# On Windows systems it is possible to install GnuPG
# as a portable application.
# In this case only this command line option is considered,
# all other ways to set a home directory are ignored.
#
# To install GnuPG as a portable application under Windows,
# create an empty file named 'gpgconf.ctl' in the same directory
# as the tool 'gpgconf.exe'.
# The root of the installation is then that directory;
# or, if 'gpgconf.exe' has been installed
# directly below a directory named 'bin', its parent directory.
# You also need to make sure that the following directories exist
# and are writable: 'ROOT/home' for the GnuPG home
# and 'ROOT/var/cache/gnupg' for internal cache files.
export GNUPGHOME="$HOME/.config/gnupg"
