#!/usr/bin/bash

setup_env() {
    BUILD_ROOT=$(mktemp -d -t build-XXXXXXXX)
    CACHE_ROOT=$(mktemp -d -t cache-XXXXXXXX)
    ENV_ROOT=$(mktemp -d -t env-XXXXXXXX)
    BIN_ROOT=$(mktemp -d -t bin-XXXXXXXX)
    buildpack=$(realpath buildpack)
    PATH="${PATH}:${BIN_ROOT}"
    
    build=${BUILD_ROOT}
    env_dir=${ENV_ROOT}
    
    export BUILD_ROOT CACHE_ROOT ENV_ROOT BIN_ROOT buildpack build env_dir
    
    create_fake_run_hook
    cd "${BUILD_ROOT}" || exit 1
}

teardown_env() {
    rm -rf "${BUILD_ROOT}" "${CACHE_ROOT}" "${ENV_ROOT}"
    
    unset BUILD_ROOT CACHE_ROOT ENV_ROOT buildpack build env_dir
}

bash_with_trap() {
    script=$1
    command=$2
    bash -c "source \"${script}\"; ${command}"
}

create_fake_run_hook() {
    cat > "${BIN_ROOT}/run_hook" << EOF
#!/usr/bin/env bash
cd "\$2" && bash "./\$3" > ".hook-\$1" 2>".hook-error-\$1" || true
EOF
    chmod +x "${BIN_ROOT}/run_hook"
}