# ShellCheck, a linter for shell scripts,
# from the project's latest release,
# checked against the SHA-256 digest GitHub publishes for it.
# The last stage holds only the tool's prefix,
# which the launcher copies into the tool's volume.
ARG BASE_IMAGE=dockered-claude-default:latest
FROM ${BASE_IMAGE} AS build

USER root
WORKDIR /opt/tools/shellcheck
RUN : \
 && case "$(uname -m)" in \
    x86_64 | aarch64) arch="$(uname -m)" ;; \
    *) echo "unsupported architecture: $(uname -m)" >&2; exit 1 ;; \
    esac \
 && tmp="$(mktemp -d)" \
 && curl -fsSL -o "${tmp}/release.json" \
    https://api.github.com/repos/koalaman/shellcheck/releases/latest \
 && jq -er --arg suffix ".linux.${arch}.tar.gz" \
    '[.assets[] | select(.name | endswith($suffix))] | first | "\(.browser_download_url) \(.digest)"' \
    "${tmp}/release.json" >"${tmp}/asset" \
 && read -r url digest <"${tmp}/asset" \
 && case "${digest}" in sha256:?*) ;; *) echo "no digest for ${url}" >&2; exit 1 ;; esac \
 && curl -fsSL -o "${tmp}/shellcheck.tar.gz" "${url}" \
 && echo "${digest#sha256:}  ${tmp}/shellcheck.tar.gz" | sha256sum -c - \
 && tar -xzf "${tmp}/shellcheck.tar.gz" --strip-components=1 -C "${tmp}" \
 && install -D -m 755 "${tmp}/shellcheck" bin/shellcheck \
 && install -D -m 644 "${tmp}/LICENSE.txt" share/doc/shellcheck/LICENSE.txt \
 && rm -rf "${tmp}" \
 && bin/shellcheck --version \
 && :

FROM scratch
COPY --from=build /opt/tools/shellcheck /opt/tools/shellcheck
