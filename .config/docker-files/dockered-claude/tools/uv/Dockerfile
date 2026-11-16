# uv, from the project's official release archive,
# for a newer uv than the base image's.
# The last stage holds only the tool's prefix,
# which the launcher copies into the tool's volume.
ARG BASE_IMAGE=dockered-claude:latest
FROM ${BASE_IMAGE} AS build

USER root
WORKDIR /opt/tools/uv
RUN : \
 && case "$(uname -m)" in \
    x86_64 | aarch64) arch="$(uname -m)" ;; \
    *) echo "unsupported architecture: $(uname -m)" >&2; exit 1 ;; \
    esac \
 && mkdir -p bin \
 && curl -fsSL -o /tmp/uv.tar.gz \
    "https://github.com/astral-sh/uv/releases/latest/download/uv-${arch}-unknown-linux-gnu.tar.gz" \
 && tar -xzf /tmp/uv.tar.gz --strip-components=1 -C bin \
 && rm /tmp/uv.tar.gz \
 && bin/uv --version \
 && :

FROM scratch
COPY --from=build /opt/tools/uv /opt/tools/uv
