#!/usr/bin/env bats

load test_utils

setup() {
    setup_env
}

teardown() {
    teardown_env
    rm -rf /tmp/build || true
}

@test "GO_INSTALL_PACKAGE_SPEC specified" {
    export GO_INSTALL_PACKAGE_SPEC=specified
    run bash_with_trap ${BUILD_PACK}/hooks/pre-compile 'echo ${GO_INSTALL_PACKAGE_SPEC}'

    [ "${status}" == 0 ]
    [ "${output}" == "specified" ]
}

@test "GO_INSTALL_PACKAGE_SPEC not specified" {
    export BKPAAS_APP_ID=app GO_BKAPP_FRAMEWORK=1
    run bash_with_trap ${BUILD_PACK}/hooks/pre-compile 'echo ${GO_INSTALL_PACKAGE_SPEC}'

    [ "${status}" == 0 ]
    [ "${output}" == "app" ]
}

@test "GO_BKAPP_FRAMEWORK not specified" {
    export BKPAAS_APP_ID=app GO_BKAPP_FRAMEWORK=0
    run bash_with_trap ${BUILD_PACK}/hooks/pre-compile 'echo ${GO_INSTALL_PACKAGE_SPEC}'

    [ "${status}" == 0 ]
    [ "${output}" == "" ]
}

@test "go version determine rules" {
    echo 'info "Detected go modules via go.mod"' > ${BUILD_PACK}/lib/common.sh

    run bash_with_trap ${BUILD_PACK}/hooks/pre-compile
    [ "${status}" == 0 ]

    run cat ${BUILD_PACK}/lib/common.sh
    [ "${status}" == 0 ]
    [[ "${output}" =~ "GOVERSION=\${GOVERSION:-\$(awk '{ if (\$1 == \"go\" ) { print \$2; exit } }' \${goMOD})}" ]]
}

@test "do not set git cred helper" {
    echo '
setGitCredHelper() {
    dosomething
}
' > ${BUILD_PACK}/lib/common.sh

    run bash_with_trap ${BUILD_PACK}/hooks/pre-compile
    [ "${status}" == 0 ]

    excepted='
setGitCredHelper() {
    return
    dosomething
}
'
    run cat ${BUILD_PACK}/lib/common.sh
    [ "${status}" == 0 ]
    [[ "${output//[[:space:]]/}" =~ "${excepted//[[:space:]]/}" ]]
}

@test "do not clear git cred helper" {
    echo '
clearGitCredHelper() {
    dosomething
}
' > ${BUILD_PACK}/lib/common.sh

    run bash_with_trap ${BUILD_PACK}/hooks/pre-compile
    [ "${status}" == 0 ]

    excepted='
clearGitCredHelper() {
    return
    dosomething
}
'
    run cat ${BUILD_PACK}/lib/common.sh
    [ "${status}" == 0 ]
    [[ "${output//[[:space:]]/}" =~ "${excepted//[[:space:]]/}" ]]
}

@test "test /tmp/build links" {
    [ ! -e "/tmp/build" ]

    run ${BUILD_PACK}/hooks/pre-compile

    run touch "/tmp/build/test"
    [ -e "test" ]
}

@test "test /tmp/build links exists" {
    mkdir -p /tmp/build

    run ${BUILD_PACK}/hooks/pre-compile

    run touch "/tmp/build/test"
    [ ! -e "test" ]
}