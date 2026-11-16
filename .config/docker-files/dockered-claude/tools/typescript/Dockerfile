# TypeScript's compiler, tsc, from npm.
# The last stage holds only the tool's prefix,
# which the launcher copies into the tool's volume.
ARG BASE_IMAGE=dockered-claude:latest
FROM ${BASE_IMAGE} AS build

USER root
RUN : \
 && npm_config_prefix=/opt/tools/typescript \
    npm install --global typescript \
 && rm -rf /root/.npm \
 && /opt/tools/typescript/bin/tsc --version \
 && :

FROM scratch
COPY --from=build /opt/tools/typescript /opt/tools/typescript
