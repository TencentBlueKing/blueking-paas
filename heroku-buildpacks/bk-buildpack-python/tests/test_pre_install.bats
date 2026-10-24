#!/usr/bin/env bats

load test_utils

setup() {
    BUILD_DIR=$(mktemp -d -t bp-pre-install-XXXXXXXX)
    CACHE_DIR=$(mktemp -d -t bp-pre-install-XXXXXXXX)
    ENV_DIR=$(mktemp -d -t bp-pre-install-XXXXXXXX)
    ROOT_DIR=$(mktemp -d -t bp-pre-install-XXXXXXXX)
    REAL_HOME=${HOME}
    HOME=${BUILD_DIR}
    BIN_DIR=${ROOT_DIR}/bin

    cp -r buildpack/* ${ROOT_DIR}

    export BUILD_DIR CACHE_DIR ENV_DIR HOME REAL_HOME ROOT_DIR BIN_DIR
}

teardown() {
    rm -rf "${BUILD_DIR}" "${CACHE_DIR}" "${ENV_DIR}" "${ROOT_DIR}"
    HOME=${REAL_HOME}

    export HOME
    unset BUILD_DIR CACHE_DIR ENV_DIR ROOT_DIR REAL_HOME
}

@test "pip config exists" {
    run bash ${ROOT_DIR}/hooks/pre-install
    [ "${status}" = 0 ]
    [ -f ~/.pip/pip.conf ]
}

@test "pip index url" {
    run env PIP_INDEX_URL=http://pypi.qq.com bash ${ROOT_DIR}/hooks/pre-install
    [ "${status}" = 0 ]

    run cat ~/.pip/pip.conf
    [[ "${output}" =~ "index-url = http://pypi.qq.com" ]]
}

@test "pip extra index url" {
    run env PIP_EXTRA_INDEX_URL=http://pypi.qq.com bash ${ROOT_DIR}/hooks/pre-install
    [ "${status}" = 0 ]

    run cat ~/.pip/pip.conf
    [[ "${output}" =~ "extra-index-url = http://pypi.qq.com" ]]
}

@test "pip trusted host" {
    run env PIP_INDEX_HOST=pypi.qq.com bash ${ROOT_DIR}/hooks/pre-install
    [ "${status}" = 0 ]

    run cat ~/.pip/pip.conf
    [[ "${output}" =~ "trusted-host = pypi.qq.com" ]]
}

@test "steps fixes" {
    run bash ${ROOT_DIR}/hooks/pre-install
    [ "${status}" = 0 ]

    run cat ${BIN_DIR}/steps/mercurial
    [ "${output}" = "#!/usr/bin/env bash" ]

    run cat ${BIN_DIR}/steps/pylibmc
    [ "${output}" = "#!/usr/bin/env bash" ]

    run cat ${BIN_DIR}/steps/cryptography
    [ "${output}" = "#!/usr/bin/env bash" ]

    run cat ${BIN_DIR}/steps/geo-libs
    [ "${output}" = "#!/usr/bin/env bash" ]

    run cat ${BIN_DIR}/steps/gdal
    [ "${output}" = "#!/usr/bin/env bash" ]
}
@test "works under set -u without pip env" {
    run env -u PIP_INDEX_URL -u PIP_EXTRA_INDEX_URL -u PIP_INDEX_HOST \
        bash -c "set -eu; BUILDPACK_DIR='${ROOT_DIR}'; source '${ROOT_DIR}/hooks/pre-install'; echo \"args=\${#BK_PIP_BOOTSTRAP_ARGS[@]}\""

    [ "${status}" = 0 ]
    [[ "${output}" =~ "args=0" ]]
}

@test "bootstrap args use main index only" {
    run env PIP_INDEX_URL=https://pypi.example.com/simple/ PIP_EXTRA_INDEX_URL=https://extra.example.com/simple/ PIP_INDEX_HOST=pypi.example.com \
        bash -c "set -eu; BUILDPACK_DIR='${ROOT_DIR}'; source '${ROOT_DIR}/hooks/pre-install'; echo \"args=\${BK_PIP_BOOTSTRAP_ARGS[*]}\""

    [ "${status}" = 0 ]
    [[ "${output}" =~ "args=--index-url https://pypi.example.com/simple/ --trusted-host pypi.example.com" ]]
}

@test "PIP_VERSION kept but no longer exported" {
    run env PIP_VERSION=26.2.2 \
        bash -c "set -eu; BUILDPACK_DIR='${ROOT_DIR}'; source '${ROOT_DIR}/hooks/pre-install'; echo \"value=\${PIP_VERSION}\"; bash -c 'echo \"child=\${PIP_VERSION:-unset}\"'"

    [ "${status}" = 0 ]
    [[ "${output}" =~ "value=26.2.2" ]]
    [[ "${output}" =~ "child=unset" ]]
}
