#!/usr/bin/env bats

load test_utils

setup() {
    setup_env
}

teardown() {
    teardown_env
}

@test "test set install flags by env file" {
    flags='-ldflags "-X config/version=v1"'
    echo "${flags}" > ${env_dir}/GO_INSTLL_ARGS

    run bash_with_trap ${buildpack}/hooks/pre-gobuild 'echo "${FLAGS[@]}"'

    [ "${status}" == 0 ]
    [ "${output}" == "${flags}" ]
}

@test "test set install flags by env var" {
    flags='-ldflags "-X config/version=v1"'
    export GO_INSTLL_ARGS="${flags}"
    run bash_with_trap ${buildpack}/hooks/pre-gobuild 'echo "${FLAGS[@]}"'

    [ "${status}" == 0 ]
    [ "${output}" == "${flags}" ]
}