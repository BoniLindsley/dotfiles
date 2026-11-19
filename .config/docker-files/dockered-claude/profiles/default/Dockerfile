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

ENV HOME=/home/claude

# The image itself is non-root even when invoked without the wrapper.
# The launcher overrides this with the invoking host user's UID/GID.
USER 65532:65532

# The launcher starts Claude Code from its tool's volume.
# Run without it, the image says so rather than failing obscurely.
ENTRYPOINT ["/bin/sh", "-c", "claude=/opt/tools/claude-code/bin/claude; if [ -x \"$claude\" ]; then exec \"$claude\" \"$@\"; fi; echo 'Claude Code is not mounted at /opt/tools/claude-code; run this image with the dockered-claude launcher.' >&2; exit 1", "claude"]
