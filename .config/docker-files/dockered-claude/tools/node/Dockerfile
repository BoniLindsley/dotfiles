# Node.js, with npm and npx, from the project's latest release,
# not a prerelease,
# checked against the SHA-256 in that release's SHASUMS256.txt.
# Node.js publishes no musl build, so a musl-based profile is refused.
# The version goes in version, so the launcher names the volume by it.
# latest-version prints the version this would install.
# The last stage holds only the tool's prefix,
# which the launcher copies into the tool's volume.
ARG BASE_IMAGE=dockered-claude-default:latest
FROM ${BASE_IMAGE} AS build

USER root
WORKDIR /opt/tools/node
RUN : \
 && case "$(uname -m)" in \
    x86_64) arch=x64 ;; \
    aarch64) arch=arm64 ;; \
    *) echo "unsupported architecture: $(uname -m)" >&2; exit 1 ;; \
    esac \
 && if ls /lib/ld-musl-* >/dev/null 2>&1; then \
      echo "Node.js publishes no musl build" >&2; exit 1; \
    fi \
 && base=https://nodejs.org/dist \
 # index.json lists prereleases too, such as 27.0.0-alpha.0.1.1,
 # and is not relied on to be sorted,
 # so the highest version without a suffix is taken.
 && version="$(curl -fsSL "${base}/index.json" | jq -er '[.[].version | select(test("^v[0-9]+[.][0-9]+[.][0-9]+$")) | ltrimstr("v") | split(".") | map(tonumber)] | max | map(tostring) | join(".")')" \
 && if ! printf '%s\n' "${version}" | grep -Eqx '[0-9]+\.[0-9]+\.[0-9]+'; then \
      echo "unexpected version from ${base}/index.json: ${version}" >&2; exit 1; \
    fi \
 && name="node-v${version}-linux-${arch}.tar.gz" \
 && tmp="$(mktemp -d)" \
 && curl -fsSL -o "${tmp}/SHASUMS256.txt" "${base}/v${version}/SHASUMS256.txt" \
 && curl -fsSL -o "${tmp}/${name}" "${base}/v${version}/${name}" \
 && (cd "${tmp}" && awk -v name="${name}" '$2 == name' SHASUMS256.txt | sha256sum -c -) \
 && tar -xzf "${tmp}/${name}" --strip-components=1 \
 && printf '%s\n' "${version}" >version \
 && rm -rf "${tmp}" \
 && bin/node --version \
 # npm runs node from PATH.
 && PATH="/opt/tools/node/bin:${PATH}" npm --version \
 && :

FROM scratch
COPY --from=build /opt/tools/node /opt/tools/node
