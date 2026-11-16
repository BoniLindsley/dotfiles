# rclone, from the project's official release archive.
# The last stage holds only the tool's prefix,
# which the launcher copies into the tool's volume.
ARG BASE_IMAGE=dockered-claude:latest
FROM ${BASE_IMAGE} AS build

USER root
WORKDIR /opt/tools/rclone
RUN : \
 && case "$(uname -m)" in \
    x86_64) arch=amd64 ;; \
    aarch64) arch=arm64 ;; \
    *) echo "unsupported architecture: $(uname -m)" >&2; exit 1 ;; \
    esac \
 && tmp="$(mktemp -d)" \
 && curl -fsSL -o "${tmp}/rclone.zip" \
    "https://downloads.rclone.org/rclone-current-linux-${arch}.zip" \
 && python3 -m zipfile -e "${tmp}/rclone.zip" "${tmp}" \
 && install -D -m 755 "${tmp}"/rclone-*-linux-"${arch}"/rclone bin/rclone \
 && rm -rf "${tmp}" \
 && bin/rclone version \
 && :

FROM scratch
COPY --from=build /opt/tools/rclone /opt/tools/rclone
