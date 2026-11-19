# TypeScript's compiler, tsc, and its language server, tsserver, from npm,
# with a Node.js of their own under node/,
# so that they run without the node tool selected.
# Only the wrappers in bin/ go on PATH,
# so this Node.js does not collide with the node tool's.
# The last stage holds only the tool's prefix,
# which the launcher copies into the tool's volume.
ARG BASE_IMAGE=dockered-claude-default:latest
FROM ${BASE_IMAGE} AS build

USER root
WORKDIR /opt/tools/typescript
# TODO: This duplicates the download in tools/node/Dockerfile,
# and the two Node.js versions can differ.
# Share it once tools can depend on one another.
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
 && mkdir node \
 && tar -xzf "${tmp}/${name}" --strip-components=1 -C node \
 && rm -rf "${tmp}" \
 && :

RUN : \
 # npm runs node from PATH.
 && PATH="/opt/tools/typescript/node/bin:${PATH}" \
    npm install --global --prefix node typescript \
 # npm is needed only to install TypeScript,
 # and the headers and documentation not at all.
 && rm -rf /root/.npm node/include node/share \
    node/bin/npm node/bin/npx node/bin/corepack \
    node/lib/node_modules/npm node/lib/node_modules/corepack \
 && mkdir bin \
 && for command in tsc tsserver; do \
      printf '%s\n' \
        '#!/bin/sh' \
        "exec /opt/tools/typescript/node/bin/node /opt/tools/typescript/node/lib/node_modules/typescript/bin/${command} \"\$@\"" \
        >"bin/${command}" \
      && chmod 755 "bin/${command}" \
      || exit 1; \
    done \
 && bin/tsc --version \
 && :

FROM scratch
COPY --from=build /opt/tools/typescript /opt/tools/typescript
