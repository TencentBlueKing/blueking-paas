#!/usr/bin/env bats

load test_utils

setup() {
    setup_env
}

teardown() {
    teardown_env
}

@test "vendor not exists" {
    [ ! -e "${BUILD_ROOT}/vendor" ]

    export WITH_CODE_FILES=0
    run "${buildpack}/hooks/post-compile"
    [ "${status}" = 0 ]
    [ ! -e "${BUILD_ROOT}/vendor" ]
}

@test "vendor exists" {
    mkdir vendor

    [ -d "${BUILD_ROOT}/vendor" ]

    export WITH_CODE_FILES=0
    run "${buildpack}/hooks/post-compile"
    [ "${status}" = 0 ]
    [ ! -e "${BUILD_ROOT}/vendor" ]
}

@test "vendor exists but WITH_CODE_FILES env set" {
    mkdir vendor

    [ -d "${BUILD_ROOT}/vendor" ]

    export WITH_CODE_FILES=1
    run "${buildpack}/hooks/post-compile"

    [ "${status}" = 0 ]
    [ -d "${BUILD_ROOT}/vendor" ]
}

@test "test gopath in post-compile hook" {
    mkdir -p "${BUILD_ROOT}/bin"
    echo 'echo "${PATH}"' > "${BUILD_ROOT}/bin/post-compile"
    
    export GOPATH="/go"
    run "${buildpack}/hooks/post-compile"
    [ "${status}" = 0 ]
    
    run cat ".hook-post-compile"
    [ "${status}" = 0 ]
    [[ "${output}" =~ "/go/bin" ]]
}

@test "test default gopath in post-compile hook" {
    mkdir -p "${BUILD_ROOT}/bin"
    echo 'echo "${PATH}"' > "${BUILD_ROOT}/bin/post-compile"
    
    export HOME="/app"
    run "${buildpack}/hooks/post-compile"
    [ "${status}" = 0 ]
    
    run cat ".hook-post-compile"
    [ "${status}" = 0 ]
    [[ "${output}" =~ "/app/go/bin" ]]
}

@test "test profile gopath.sh" {
    run "${buildpack}/hooks/post-compile"
    [ "${status}" = 0 ]

    run cat "${build}/.profile.d/gopath.sh"
    [ "${status}" = 0 ]
    [[ "${output}" =~ "GOPATH=\$HOME/go" ]]
    [[ "${output}" =~ "PATH=\$PATH:\$GOPATH/bin:\$HOME/bin" ]]
}

@test "gopath not exists" {
    export GOPATH="${BIN_ROOT}/gopath_no_exists"
    export HOME="${BUILD_ROOT}"

    run "${buildpack}/hooks/post-compile"

    [ -d "${BUILD_ROOT}/go/bin" ]
}

@test "gopath exists" {
    export GOPATH="${BIN_ROOT}/gopath_exists"
    export HOME="${BUILD_ROOT}"

    mkdir -p "${GOPATH}/bin"
    touch "${GOPATH}/bin/command"

    run "${buildpack}/hooks/post-compile"

    [ -d "${BUILD_ROOT}/go/bin" ]
    [ -e "${BUILD_ROOT}/go/bin/command" ]
}

@test "go exists" {
    export GOPATH="${BUILD_ROOT}/go"
    export HOME="${BUILD_ROOT}"

    mkdir -p "${GOPATH}/bin"
    touch "${GOPATH}/bin/command"

    run "${buildpack}/hooks/post-compile"

    [ -d "${BUILD_ROOT}/go/bin" ]
    [ -e "${BUILD_ROOT}/go/bin/command" ]
}

@test "gopath not set" {
    export HOME="${BUILD_ROOT}"

    mkdir -p "${BUILD_ROOT}/go/bin"
    touch "${BUILD_ROOT}/go/bin/command"

    run "${buildpack}/hooks/post-compile"

    [ -d "${BUILD_ROOT}/go/bin" ]
    [ -e "${BUILD_ROOT}/go/bin/command" ]
}