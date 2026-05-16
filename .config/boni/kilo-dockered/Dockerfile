# ################################################################
# ### Install system packages and drop down to non-root.
FROM debian:bookworm-slim

RUN \
    apt-get update \
 && apt-get install \
      --assume-yes \
      --no-install-recommends \
      # Download
      ca-certificates \
      curl \
      # Node.js runtime. Also needed by Kilo.
      nodejs \
      npm \
 && rm -rf /var/lib/apt/lists/*

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

# ################################################################
# ### Make Node.js and Kilo available
ENV NPM_CONFIG_PREFIX='/home/dev/opt/node'
ENV PATH="${NPM_CONFIG_PREFIX}/bin:${PATH}"

RUN \
    mkdir -p "${NPM_CONFIG_PREFIX}" \
 && npm install --global @kilocode/cli

# ################################################################
# ### Set up directories to be mounted into.
RUN mkdir -p '/home/dev/.cache' '/home/dev/.local' workspace
WORKDIR workspace
ENTRYPOINT ["kilo"]
CMD []
