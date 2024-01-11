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
    #rm -rf "${BUILD_DIR}" "${CACHE_DIR}" "${ENV_DIR}" "${BUILD_PACK}"
    HOME=${REAL_HOME}

    export HOME
    unset BUILD_DIR CACHE_DIR ENV_DIR BUILD_PACK REAL_HOME
}

@test "compile hook created" {
    mkdir -p ${BUILD_DIR}/bin
    run "${BUILD_PACK}/hooks/setup-user-compile-hook"

    run cat "${BUILD_DIR}/bin/pre_compile"
    [ "${status}" = 0 ]
    [[ "${output}" =~ "trace_call" ]]
    [[ "${output}" =~ "${BUILD_DIR}/bin/pre-compile" ]]

    run cat "${BUILD_DIR}/bin/post_compile"
    [ "${status}" = 0 ]
    [[ "${output}" =~ "trace_call" ]]
    [[ "${output}" =~ "${BUILD_DIR}/bin/post-compile" ]]
}

@test "compile hook not create because bin directory not exists" {
    run "${BUILD_PACK}/hooks/setup-user-compile-hook"

    [ "${status}" = 0 ]
    [ ! -f "${BUILD_DIR}/bin/pre_compile" ]
    [ ! -f "${BUILD_DIR}/bin/post_compile" ]
}

@test "compile hook not create because already exists" {
    mkdir -p ${BUILD_DIR}/bin
    touch ${BUILD_DIR}/bin/pre_compile
    touch ${BUILD_DIR}/bin/post_compile
    run "${BUILD_PACK}/hooks/setup-user-compile-hook"

    [ "${status}" = 0 ]

    run cat "${BUILD_DIR}/bin/pre_compile"
    [ "${status}" = 0 ]
    [ "${output}" = "" ]

    run cat "${BUILD_DIR}/bin/post_compile"
    [ "${status}" = 0 ]
    [ "${output}" = "" ]
}

@test "trace_call hook" {
    mkdir -p ${BUILD_DIR}/bin
    run "${BUILD_PACK}/hooks/setup-user-compile-hook"
    echo "I'm Groooooot!" > ${BUILD_DIR}/bin/pre-compile

    [ "${status}" = 0 ]

    run hooked_bash 'shopt -s expand_aliases; alias trace_call=cat' "${BUILD_DIR}/bin/pre_compile"
    [ "${status}" = 0 ]
    [ "${output}" = "I'm Groooooot!" ]
}

@test "make sure script executable" {
    mkdir -p ${BUILD_DIR}/bin
    "${BUILD_PACK}/hooks/setup-user-compile-hook"
    echo "" > ${BUILD_DIR}/bin/pre-compile

    hooked_bash 'shopt -s expand_aliases; alias trace_call=cat' "${BUILD_DIR}/bin/pre_compile"

    run command -v "${BUILD_DIR}/bin/pre-compile"
    [ "${status}" = 0 ]
    [ "${output}" = "${BUILD_DIR}/bin/pre-compile" ]
}

@test "make sure failed when hook error" {
    mkdir -p ${BUILD_DIR}/bin
    "${BUILD_PACK}/hooks/setup-user-compile-hook"
    echo "" > ${BUILD_DIR}/bin/pre-compile

    run hooked_bash 'shopt -s expand_aliases; alias trace_call=false' "${BUILD_DIR}/bin/pre_compile"

    [ "${status}" = 1 ]
}

@test "make sure script not exists after run" {
    mkdir -p ${BUILD_DIR}/bin
    "${BUILD_PACK}/hooks/setup-user-compile-hook"
    echo "" > ${BUILD_DIR}/bin/pre-compile

    run hooked_bash 'shopt -s expand_aliases; alias trace_call=cat' "${BUILD_DIR}/bin/pre_compile"

    [ "${status}" = 0 ]
    [ ! -f "${BUILD_DIR}/bin/pre_compile" ]
}
