FROM debian:latest

# Package choices
RUN : \
 && apt-get update \
 && apt-get install \
    --assume-yes \
    --no-install-recommends \
     # Shell and basic utilities
     bash \
     ca-certificates \
     coreutils \
     curl \
     file \
     findutils \
     gzip \
     jq \
     less \
     procps \
     ripgrep \
     tar \
     \
     # Claude Code's sandbox on Linux uses bubblewrap and socat
     bubblewrap \
     socat \
     \
     # Version control and development
     git \
     openssh-client \
     patch \
     \
     # Compilers and native dependencies
     build-essential \
     pkg-config \
     \
     # C and C++ build systems, debugging and documentation
     cmake \
     doxygen \
     gdb \
     graphviz \
     libcap2-bin \
     ninja-build \
     \
     # Autotools, parser generators and archivers,
     # which many vcpkg ports and source distributions need to build
     autoconf \
     autoconf-archive \
     automake \
     bison \
     flex \
     libtool \
     libtool-bin \
     unzip \
     zip \
     \
     # Python
     python3 \
     python3-dev \
     python3-pip \
     python3-venv \
 # The container runs as a non-root user,
 # so the CAP_SYS_PTRACE that the launcher adds
 # only reaches gdb through a file capability.
 # It lets gdb attach to processes it did not start (gdb -p),
 # which the host's Yama ptrace_scope of 1 otherwise forbids.
 && setcap cap_sys_ptrace+ep "$(readlink -f /usr/bin/gdb)" \
 && getcap "$(readlink -f /usr/bin/gdb)" | grep -q cap_sys_ptrace \
 && rm -rf /var/lib/apt/lists/* \
 && :

# Install uv and uvx from Astral's official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# A self-contained Node.js environment, like a Python venv: node, npm and
# every globally installed package live under one prefix. npm defaults its
# global prefix to the directory above the running node binary, so with
# ${NODE_ENV_DIR}/bin first on PATH, `npm install --global` lands here too.
ENV NODE_ENV_DIR=/opt/node
ENV PATH="${NODE_ENV_DIR}/bin:${PATH}"

# Debian's nodejs and npm only bootstrap the environment and are purged in
# the same layer: the system npm installs `n` into the environment, `n`
# installs the latest Node.js (with its npm) into the same prefix, and the
# environment's own npm then removes `n`. `n`'s download cache is deleted.
RUN : \
 && apt-get update \
 && apt-get install \
    --assume-yes \
    --no-install-recommends \
     nodejs \
     npm \
 && /usr/bin/npm install --global --prefix "${NODE_ENV_DIR}" n \
 && N_PREFIX="${NODE_ENV_DIR}" "${NODE_ENV_DIR}/bin/n" latest \
 && apt-get purge --assume-yes --auto-remove nodejs npm \
 && rm -rf /var/lib/apt/lists/* /usr/lib/node_modules \
 && hash -r \
 && test "$(command -v node)" = "${NODE_ENV_DIR}/bin/node" \
 && test "$(command -v npm)" = "${NODE_ENV_DIR}/bin/npm" \
 && test "$(npm prefix --global)" = "${NODE_ENV_DIR}" \
 && npm uninstall --global n \
 && rm -rf "${NODE_ENV_DIR}/n" /root/.npm \
 && node --version \
 && npm --version \
 && :

# npm blocks install scripts of packages not covered by allowScripts,
# and Claude Code needs its postinstall (node install.cjs)
# to set up the claude command.
# Only that package's scripts are allowed.
RUN : \
 && npm install \
    --allow-scripts=@anthropic-ai/claude-code \
    --global \
    --include=optional \
    @anthropic-ai/claude-code@latest \
 && rm -rf /root/.npm \
 && test "$(command -v claude)" = "${NODE_ENV_DIR}/bin/claude" \
 && :

ENV HOME=/home/claude

# The root filesystem is read-only at runtime, so self-updates cannot work.
# Update by rebuilding the image instead (launcher: --build).
ENV DISABLE_AUTOUPDATER=1

# The image itself is non-root even when invoked without the wrapper.
# The launcher overrides this with the invoking host user's UID/GID.
USER 65532:65532

ENTRYPOINT ["claude"]
