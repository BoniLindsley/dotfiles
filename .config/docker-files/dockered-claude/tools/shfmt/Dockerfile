# shfmt, a formatter for shell scripts,
# from the project's latest release,
# checked against the SHA-256 digest GitHub publishes for it.
# The last stage holds only the tool's prefix,
# which the launcher copies into the tool's volume.
ARG BASE_IMAGE=dockered-claude-default:latest
FROM ${BASE_IMAGE} AS build

USER root
WORKDIR /opt/tools/shfmt
RUN : \
 && case "$(uname -m)" in \
    x86_64) arch=amd64 ;; \
    aarch64) arch=arm64 ;; \
    *) echo "unsupported architecture: $(uname -m)" >&2; exit 1 ;; \
    esac \
 && tmp="$(mktemp -d)" \
 && curl -fsSL -o "${tmp}/release.json" \
    https://api.github.com/repos/mvdan/sh/releases/latest \
 && jq -er --arg suffix "_linux_${arch}" \
    '[.assets[] | select(.name | endswith($suffix))] | first | "\(.browser_download_url) \(.digest)"' \
    "${tmp}/release.json" >"${tmp}/asset" \
 && read -r url digest <"${tmp}/asset" \
 && case "${digest}" in sha256:?*) ;; *) echo "no digest for ${url}" >&2; exit 1 ;; esac \
 && curl -fsSL -o "${tmp}/shfmt" "${url}" \
 && echo "${digest#sha256:}  ${tmp}/shfmt" | sha256sum -c - \
 && install -D -m 755 "${tmp}/shfmt" bin/shfmt \
 && rm -rf "${tmp}" \
 && bin/shfmt --version \
 && :

FROM scratch
COPY --from=build /opt/tools/shfmt /opt/tools/shfmt
