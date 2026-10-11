FROM debian:latest

# Package choices
RUN : \
 && apt-get update \
 && apt-get install \
    --assume-yes \
    --no-install-recommends \
     # Shell and basic utilities
     bash \
     bubblewrap \
     ca-certificates \
     coreutils \
     curl \
     file \
     findutils \
     gzip \
     less \
     procps \
     ripgrep \
     tar \
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
     # Python
     python3 \
     python3-dev \
     python3-pip \
     python3-venv \
     \
     # Node.js
     nodejs \
     npm \
 && rm -rf /var/lib/apt/lists/* \
 && :

# Install uv and uvx from Astral's official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN : \
 && npm install \
    --global \
    --include=optional \
    --prefix /opt/npm \
    @openai/codex@latest \
 && :

ENV HOME=/home/codex
ENV PATH="/opt/npm/bin:${PATH}"

# The image itself is non-root even when invoked without the wrapper.
# The launcher overrides this with the invoking host user's UID/GID.
USER 65532:65532

ENTRYPOINT ["codex"]
