#!/usr/bin/env bats

load test_utils

setup() {
    BUILD_DIR=$(mktemp -d -t bp-pre-install-XXXXXXXX)
    CACHE_DIR=$(mktemp -d -t bp-pre-install-XXXXXXXX)
    ENV_DIR=$(mktemp -d -t bp-pre-install-XXXXXXXX)
    BUILD_PACK=$(mktemp -d -t bp-pre-install-XXXXXXXX)
    REAL_HOME=${HOME}
    HOME=${BUILD_DIR}
    ROOT_DIR=${BUILD_PACK}
    BIN_DIR=${ROOT_DIR}/bin

    cp -r buildpack/* ${BUILD_PACK}

    export BUILD_DIR CACHE_DIR ENV_DIR BUILD_PACK HOME REAL_HOME ROOT_DIR BIN_DIR
}

teardown() {
    rm -rf "${BUILD_DIR}" "${CACHE_DIR}" "${ENV_DIR}" "${BUILD_PACK}"
    HOME=${REAL_HOME}

    export HOME
    unset BUILD_DIR CACHE_DIR ENV_DIR BUILD_PACK REAL_HOME
}

@test "pip config exists" {
    run bash ${BUILD_PACK}/hooks/pre-install
    [ "${status}" = 0 ]
    [ -f ~/.pip/pip.conf ]
}

@test "pip index url" {
    run env PIP_INDEX_URL=http://pypi.qq.com bash ${BUILD_PACK}/hooks/pre-install
    [ "${status}" = 0 ]

    run cat ~/.pip/pip.conf
    [[ "${output}" =~ "index-url = http://pypi.qq.com" ]]
}

@test "pip extra index url" {
    run env PIP_EXTRA_INDEX_URL=http://pypi.qq.com bash ${BUILD_PACK}/hooks/pre-install
    [ "${status}" = 0 ]

    run cat ~/.pip/pip.conf
    [[ "${output}" =~ "extra-index-url = http://pypi.qq.com" ]]
}

@test "pip trusted host" {
    run env PIP_INDEX_HOST=pypi.qq.com bash ${BUILD_PACK}/hooks/pre-install
    [ "${status}" = 0 ]

    run cat ~/.pip/pip.conf
    [[ "${output}" =~ "trusted-host = pypi.qq.com" ]]
}

@test "default pip version" {
    export PIP_UPDATE="0.0.0"
    run bash_with_trap ${BUILD_PACK}/hooks/pre-install 'echo ${PIP_UPDATE}'
    [ "${status}" = 0 ]
    [ "${output}" = "0.0.0" ]
}

@test "specified pip version" {
    export PIP_VERSION="x.x.x"
    run bash_with_trap ${BUILD_PACK}/hooks/pre-install 'echo ${PIP_UPDATE}'
    [ "${status}" = 0 ]
    [ "${output}" = "x.x.x" ]
}

@test "unset pip version" {
    export PIP_VERSION="x.x.x"
    run bash_with_trap ${BUILD_PACK}/hooks/pre-install 'echo ${PIP_VERSION}'
    [ "${status}" = 0 ]
    [ "${output}" = "" ]
}

@test "steps fixes" {
    run bash ${BUILD_PACK}/hooks/pre-install
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