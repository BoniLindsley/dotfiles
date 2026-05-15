# ################################################################
# ### Install system packages and drop down to non-root.
FROM debian:bookworm-slim AS base

RUN \
    apt-get update \
 && apt-get install \
      --assume-yes \
      --no-install-recommends \
      # Download
      ca-certificates \
      curl \
      # Version control. Also needed by vim-plugged.
      git \
      # Development. Also used by nvim-treesitter.
      g++ \
      gcc \
      make \
      # Terminal utilities
      fd-find \
      ripgrep \
      xclip \
      # Locale
      locales \
      # Node.js runtime. Also needed by Kilo.
      nodejs \
      npm \
 && rm -rf /var/lib/apt/lists/*

# UTF-8 locale. Neovim requires a real locale.
RUN \
    sed -i '/en_US.UTF-8/s/^# //' /etc/locale.gen \
 && locale-gen

# Only use root for installing system packages.
# Everything else is owned by user.
RUN \
    groupadd \
      --gid 1000 \
      dev \
 && useradd \
      --create-home \
      --gid 1000 \
      --shell /bin/bash \
      --uid 1000 \
      dev
USER dev
WORKDIR /home/dev
ENV \
  LANG=en_US.UTF-8 \
  LANGUAGE=en_US:en \
  LC_ALL=en_US.UTF-8 \
  XDG_CONFIG_HOME='/home/dev/.config' \
  XDG_DATA_HOME='/home/dev/.local/share' \
  XDG_CACHE_HOME='/home/dev/.cache'

# ################################################################
# ### Use uv to make Python and tools available
ENV UV_INSTALL_DIR='/home/dev/opt/uv'
ENV UV_TOOL_BIN_DIR="${UV_INSTALL_DIR}/bin"
RUN \
     curl \
       --fail \
       --location 'https://astral.sh/uv/install.sh' \
       --show-error \
       --silent \
   | sh
ENV PATH="${UV_INSTALL_DIR}:${UV_TOOL_BIN_DIR}:${PATH}"

RUN \
    uv python install 3.12 \
 && uv tool install mypy \
 && uv tool install pylint \
 && uv tool install pytest

# ################################################################
# ### Make Node.js and Kilo
ENV NPM_CONFIG_PREFIX='/home/dev/opt/node'
ENV PATH="${NPM_CONFIG_PREFIX}/bin:${PATH}"

RUN \
    mkdir -p "${NPM_CONFIG_PREFIX}" \
 && npm install --global @kilocode/cli

# ################################################################
# ### Make Neovim available and set up plugins
RUN \
    mkdir -p opt/nvim \
 && NVIM_VERSION=$( \
        curl \
           --fail \
           --location 'https://api.github.com/repos/neovim/neovim/releases/latest' \
           --show-error \
           --silent \
      | grep '"tag_name"' \
      | head -1 \
      | cut --delimiter '"' --fields 4 \
    ) \
 && curl \
      --fail \
      --location "https://github.com/neovim/neovim/releases/download/${NVIM_VERSION}/nvim-linux-x86_64.tar.gz" \
      --show-error \
      --silent \
  | tar --directory=opt/nvim --extract --gzip --strip-components=1

ENV PATH="/home/dev/opt/nvim/bin:${PATH}"

RUN mkdir -p '/home/dev/.config/nvim' '/home/dev/.config/vim'
COPY --chown=dev:dev '.config/nvim' '/home/dev/.config/nvim'
COPY --chown=dev:dev '.config/vim' '/home/dev/.config/vim'
RUN env HOME='/home/dev' nvim --headless -c 'PlugUpdate' -c 'qa'

# ################################################################
# ### Set up a directory to be mounted into.
RUN mkdir -p work
WORKDIR work
CMD ["nvim"]
