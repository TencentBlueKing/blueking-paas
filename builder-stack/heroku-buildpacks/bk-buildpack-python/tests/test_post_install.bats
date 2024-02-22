#!/usr/bin/env bats

load test_utils

setup() {
    BUILD_DIR=$(mktemp -d -t bp-post-install-XXXXXXXX)
    CACHE_DIR=$(mktemp -d -t bp-post-install-XXXXXXXX)
    ENV_DIR=$(mktemp -d -t bp-post-install-XXXXXXXX)
    ROOT_DIR=$(mktemp -d -t bp-post-install-XXXXXXXX)
    APP_DIR=$(mktemp -d -t bp-post-install-XXXXXXXX)

    cp -r buildpack/* ${ROOT_DIR}
    mkdir -p "${BUILD_DIR}/.heroku"

    export BUILD_DIR CACHE_DIR ENV_DIR ROOT_DIR APP_DIR
}

teardown() {
    rm -rf "${BUILD_DIR}" "${CACHE_DIR}" "${ENV_DIR}" "${ROOT_DIR}" "${APP_DIR}"

    unset BUILD_DIR CACHE_DIR ENV_DIR ROOT_DIR APP_DIR
}

@test "copy .heroku/src" {
    mkdir -p ${APP_DIR}/.heroku/src
    touch ${APP_DIR}/.heroku/src/test

    run bash -c "source ${ROOT_DIR}/bin/utils; source ${ROOT_DIR}/hooks/post-install"

    [ "${status}" = 0 ]
    [ -f "${BUILD_DIR}/.heroku/src/test" ]
}

@test "export enviroments" {
    run "${ROOT_DIR}/hooks/post-install"

    [ "${status}" = 0 ]
    [ -f "${ROOT_DIR}/export" ]
}

@test "clean pycache" {
    test_path="${BUILD_DIR}/.heroku/python/lib/python/site-packages/__pycache__/x"

    mkdir -p $(dirname "${test_path}")
    touch "${test_path}"
    [ -f "${test_path}" ]

    run "${ROOT_DIR}/hooks/post-install"

    [ "${status}" = 0 ]
    [ ! -f "${test_path}" ]
}

@test "clean pyc" {
    test_path="${BUILD_DIR}/.heroku/python/lib/python/site-packages/x.pyc"

    mkdir -p $(dirname "${test_path}")
    touch "${test_path}"
    [ -f "${test_path}" ]

    run "${ROOT_DIR}/hooks/post-install"

    [ "${status}" = 0 ]
    [ ! -f "${test_path}" ]
}