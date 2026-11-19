# Claude Code, from Anthropic's native build
# of the release channel CHANNEL (latest or stable),
# checked against the SHA-256 in that release's manifest,
# as Anthropic's install.sh does,
# but without running install.sh or `claude install`.
# The musl build is chosen on a musl-based profile.
# The version goes in version, so the launcher names the volume by it.
# latest-version prints the version this would install, from the same channel.
# The last stage holds only the tool's prefix,
# which the launcher copies into the tool's volume.
ARG BASE_IMAGE=dockered-claude-default:latest
FROM ${BASE_IMAGE} AS build

ARG CHANNEL=latest

USER root
WORKDIR /opt/tools/claude-code
RUN : \
 && case "$(uname -m)" in \
    x86_64) arch=x64 ;; \
    aarch64) arch=arm64 ;; \
    *) echo "unsupported architecture: $(uname -m)" >&2; exit 1 ;; \
    esac \
 && if ls /lib/ld-musl-* >/dev/null 2>&1; then \
      platform="linux-${arch}-musl"; \
    else \
      platform="linux-${arch}"; \
    fi \
 && base=https://downloads.claude.ai/claude-code-releases \
 && version="$(curl -fsSL "${base}/${CHANNEL}")" \
 && if ! printf '%s\n' "${version}" | grep -Eqx '[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?'; then \
      echo "unexpected version from ${base}/${CHANNEL}: ${version}" >&2; exit 1; \
    fi \
 && tmp="$(mktemp -d)" \
 && curl -fsSL -o "${tmp}/manifest.json" "${base}/${version}/manifest.json" \
 && checksum="$(jq -er --arg platform "${platform}" \
    '.platforms[$platform].checksum' "${tmp}/manifest.json")" \
 && if ! printf '%s\n' "${checksum}" | grep -Eqx '[0-9a-f]{64}'; then \
      echo "no checksum for ${platform} in ${version}'s manifest" >&2; exit 1; \
    fi \
 && curl -fsSL -o "${tmp}/claude" "${base}/${version}/${platform}/claude" \
 && echo "${checksum}  ${tmp}/claude" | sha256sum -c - \
 && install -D -m 755 "${tmp}/claude" bin/claude \
 && printf '%s\n' "${version}" >version \
 && HOME="${tmp}" DISABLE_AUTOUPDATER=1 bin/claude --version \
 && rm -rf "${tmp}" \
 && :

FROM scratch
COPY --from=build /opt/tools/claude-code /opt/tools/claude-code
