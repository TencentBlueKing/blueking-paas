#!/usr/bin/env bats

load test_utils

setup() {
    BUILD_DIR=$(mktemp -d -t bp-pre-install-deps-XXXXXXXX)
    ROOT_DIR=$(mktemp -d -t bp-pre-install-deps-XXXXXXXX)

    cp -r buildpack/* ${ROOT_DIR}
    BUILDPACK_DIR="${ROOT_DIR}"

    write_uv_lock
    cp "${BUILD_DIR}/uv.lock" "${BUILD_DIR}/uv.lock.orig"
    printf '[project]\nname = "demo"\nversion = "0.1.0"\n' > "${BUILD_DIR}/pyproject.toml"

    export BUILD_DIR ROOT_DIR BUILDPACK_DIR
}

teardown() {
    rm -rf "${BUILD_DIR}" "${ROOT_DIR}"

    unset BUILD_DIR ROOT_DIR BUILDPACK_DIR PIP_INDEX_URL UV_DEFAULT_INDEX
}

# Source the hooks the way bin/compile does, then run the given commands in the same shell.
run_hooks() {
    local manager="$1"
    local commands="$2"
    run bash -c "
        set -eu
        source '${ROOT_DIR}/lib/output.sh'
        package_manager='${manager}'
        source '${ROOT_DIR}/hooks/pre-install-dependencies'
        ${commands}
    "
}

# A lock mixing a PyPI package, a private-index package, a direct URL dependency and the project itself.
write_uv_lock() {
    cat > "${BUILD_DIR}/uv.lock" <<'EOF'
version = 1
requires-python = ">=3.14"

[[package]]
name = "demo"
version = "0.1.0"
source = { virtual = "." }

[[package]]
name = "internal-lib"
version = "1.0.0"
source = { registry = "https://private.example.com/simple" }
wheels = [
    { url = "https://private.example.com/packages/internal_lib-1.0.0-py3-none-any.whl", hash = "sha256:aaa" },
]

[[package]]
name = "pinned-wheel"
version = "2.0.0"
source = { url = "https://files.pythonhosted.org/packages/aa/bb/pinned_wheel-2.0.0-py3-none-any.whl" }
wheels = [
    { url = "https://files.pythonhosted.org/packages/aa/bb/pinned_wheel-2.0.0-py3-none-any.whl", hash = "sha256:bbb" },
]

[[package]]
name = "six"
version = "1.17.0"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "https://files.pythonhosted.org/packages/94/e7/six-1.17.0.tar.gz", hash = "sha256:ccc" }
wheels = [
    { url = "https://files.pythonhosted.org/packages/b7/ce/six-1.17.0-py2.py3-none-any.whl", hash = "sha256:ddd" },
]
EOF
}

assert_lock_unchanged() {
    cmp "${BUILD_DIR}/uv.lock" "${BUILD_DIR}/uv.lock.orig"
}

@test "only pypi packages in uv lock are rewritten" {
    export PIP_INDEX_URL="https://pypi.example.com/simple/"

    # 退出 shell 时 EXIT trap 会还原锁文件，所以要在同一个 shell 里查看改写结果。
    run_hooks uv 'echo "index=${UV_DEFAULT_INDEX}"; cat "${BUILD_DIR}/uv.lock"'

    [ "${status}" = 0 ]
    [[ "${output}" =~ "Using PyPI mirror for uv: https://pypi.example.com/simple" ]]
    [[ "${output}" =~ "index=https://pypi.example.com/simple" ]]
    [[ "${output}" =~ 'source = { registry = "https://pypi.example.com/simple" }' ]]
    [[ "${output}" =~ "https://pypi.example.com/packages/94/e7/six-1.17.0.tar.gz" ]]
    [[ "${output}" =~ "https://pypi.example.com/packages/b7/ce/six-1.17.0-py2.py3-none-any.whl" ]]
    [[ "${output}" =~ 'hash = "sha256:ddd"' ]]
    # 私有索引与 direct URL 依赖保持原样。
    [[ "${output}" =~ 'source = { registry = "https://private.example.com/simple" }' ]]
    [[ "${output}" =~ 'source = { url = "https://files.pythonhosted.org/packages/aa/bb/pinned_wheel-2.0.0-py3-none-any.whl" }' ]]
    [[ "${output}" =~ '{ url = "https://files.pythonhosted.org/packages/aa/bb/pinned_wheel-2.0.0-py3-none-any.whl", hash = "sha256:bbb" }' ]]
}

@test "uv lock restored and index unset after install" {
    export PIP_INDEX_URL="https://pypi.example.com/simple"

    run_hooks uv "source '${ROOT_DIR}/hooks/post-install-dependencies'; echo \"index=\${UV_DEFAULT_INDEX:-unset}\""

    [ "${status}" = 0 ]
    [[ "${output}" =~ "index=unset" ]]
    assert_lock_unchanged
}

@test "uv lock restored when dependency install exits" {
    export PIP_INDEX_URL="https://pypi.example.com/simple"

    run_hooks uv 'exit 1'

    [ "${status}" = 1 ]
    assert_lock_unchanged
}

@test "mirror url is replaced literally" {
    export PIP_INDEX_URL='https://user:p&ss#1@pypi.example.com/simple'

    run_hooks uv 'cat "${BUILD_DIR}/uv.lock"'

    [ "${status}" = 0 ]
    [[ "${output}" =~ "Using PyPI mirror for uv: https://***@pypi.example.com/simple" ]]
    [[ "${output}" =~ 'registry = "https://user:p&ss#1@pypi.example.com/simple"' ]]
    [[ "${output}" =~ "https://user:p&ss#1@pypi.example.com/packages/b7/ce/six-1.17.0-py2.py3-none-any.whl" ]]
}

@test "skipped when pyproject configures uv index" {
    export PIP_INDEX_URL="https://pypi.example.com/simple"
    printf '\n[[tool.uv.index]]\nurl = "https://pypi.org/simple"\ndefault = true\n' >> "${BUILD_DIR}/pyproject.toml"

    run_hooks uv 'echo "index=${UV_DEFAULT_INDEX:-unset}"'

    [ "${status}" = 0 ]
    [[ "${output}" =~ "Skipping PyPI mirror for uv: uv index is configured by the app" ]]
    [[ "${output}" =~ "index=unset" ]]
    assert_lock_unchanged
}

@test "skipped when pyproject sets tool.uv index-url" {
    export PIP_INDEX_URL="https://pypi.example.com/simple"
    printf '\n[tool.uv]\nindex-url = "https://pypi.org/simple"\n' >> "${BUILD_DIR}/pyproject.toml"

    run_hooks uv 'echo "index=${UV_DEFAULT_INDEX:-unset}"'

    [ "${status}" = 0 ]
    [[ "${output}" =~ "Skipping PyPI mirror for uv" ]]
    assert_lock_unchanged
}

@test "skipped when uv.toml configures index" {
    export PIP_INDEX_URL="https://pypi.example.com/simple"
    printf '[[index]]\nurl = "https://pypi.org/simple"\n' > "${BUILD_DIR}/uv.toml"

    run_hooks uv 'true'

    [ "${status}" = 0 ]
    [[ "${output}" =~ "Skipping PyPI mirror for uv" ]]
    assert_lock_unchanged
}

@test "unrelated tool.uv settings do not skip" {
    export PIP_INDEX_URL="https://pypi.example.com/simple"
    printf '\n[tool.uv]\npackage = false\n\n[tool.uv.sources]\nfoo = { index = "bar" }\n' >> "${BUILD_DIR}/pyproject.toml"

    run_hooks uv 'echo "index=${UV_DEFAULT_INDEX:-unset}"'

    [ "${status}" = 0 ]
    [[ "${output}" =~ "index=https://pypi.example.com/simple" ]]
}

@test "existing UV_DEFAULT_INDEX kept" {
    export PIP_INDEX_URL="https://pypi.example.com/simple"
    export UV_DEFAULT_INDEX="https://custom.example.com/simple"

    run_hooks uv "source '${ROOT_DIR}/hooks/post-install-dependencies'; echo \"index=\${UV_DEFAULT_INDEX}\""

    [ "${status}" = 0 ]
    [[ "${output}" =~ "Skipping PyPI mirror for uv" ]]
    [[ "${output}" =~ "index=https://custom.example.com/simple" ]]
    assert_lock_unchanged
}

@test "skipped when mirror layout unknown" {
    export PIP_INDEX_URL="https://pypi.example.com/repository/pypi"

    run_hooks uv 'echo "index=${UV_DEFAULT_INDEX:-unset}"'

    [ "${status}" = 0 ]
    [[ "${output}" =~ "Skipping PyPI mirror for uv: PIP_INDEX_URL doesn't end with /simple" ]]
    [[ "${output}" =~ "index=unset" ]]
    assert_lock_unchanged
}

@test "uv lock without pypi untouched" {
    export PIP_INDEX_URL="https://pypi.example.com/simple"
    sed -i '/name = "six"/,$d' "${BUILD_DIR}/uv.lock"
    cp "${BUILD_DIR}/uv.lock" "${BUILD_DIR}/uv.lock.orig"

    run_hooks uv 'echo "index=${UV_DEFAULT_INDEX:-unset}"'

    [ "${status}" = 0 ]
    [[ "${output}" =~ "index=unset" ]]
    assert_lock_unchanged
}

@test "nothing changed without PIP_INDEX_URL" {
    run_hooks uv 'echo "index=${UV_DEFAULT_INDEX:-unset}"'

    [ "${status}" = 0 ]
    [[ "${output}" =~ "index=unset" ]]
    assert_lock_unchanged
}

@test "poetry and pipenv are not redirected" {
    export PIP_INDEX_URL="https://pypi.example.com/simple"

    for manager in poetry pipenv pip; do
        run_hooks "${manager}" 'echo "index=${UV_DEFAULT_INDEX:-unset} pipenv=${PIPENV_PYPI_MIRROR:-unset}"'

        [ "${status}" = 0 ]
        [[ "${output}" =~ "index=unset pipenv=unset" ]]
        assert_lock_unchanged
    done
}
