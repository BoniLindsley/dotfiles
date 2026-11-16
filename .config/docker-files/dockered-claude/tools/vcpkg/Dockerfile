# vcpkg, from a full clone of its repository,
# since manifests pin port versions to commits in its history
# (builtin-baseline).
# The last stage holds only the tool's prefix,
# which the launcher copies into the tool's volume.
ARG BASE_IMAGE=dockered-claude:latest
FROM ${BASE_IMAGE} AS build

USER root
WORKDIR /opt/tools/vcpkg
RUN : \
 && git clone https://github.com/microsoft/vcpkg root \
 && root/bootstrap-vcpkg.sh -disableMetrics \
 # The root is mounted read-only,
 # so vcpkg must run in manifest mode,
 # with build trees in vcpkg_installed/ of the project
 # and downloads and binary caches in ~/.cache/vcpkg.
 && printf '%s\n' '{"readonly": true}' >root/vcpkg-bundle.json \
 && mkdir -p bin \
 && ln -s ../root/vcpkg bin/vcpkg \
 && bin/vcpkg version \
 && :

FROM scratch
COPY --from=build /opt/tools/vcpkg /opt/tools/vcpkg
