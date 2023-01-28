# dotfiles

```sh
# Dependencies.
sudo apt install --no-install-recommends ca-certificates curl git

# Get and load script. Check the script before sourcing.
curl 'https://raw.githubusercontent.com/BoniLindsley/dotfiles/main/.config/bash/rc.d/50-dotshare.bashrc' > 50-dotshare.bashrc
source 50-dotshare.bashrc

# Set environment variables and fetch dotfiles.
dotshare-export-public
dotshare-clone 'https://github.com/BoniLindsley/dotfiles.git'

# Use as a normal Git working tree.
dotshare-export-public
git status
```
