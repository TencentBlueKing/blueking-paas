#!/usr/bin/bash

create_runtime_txt() {
    echo "$1" > "${BUILD_DIR}/runtime.txt"
}

bash_with_trap() {
    script=$1
    command=$2
    bash -c "source \"${script}\"; ${command}"
}

hooked_bash() {
    script=$1
    command=$2
    hook=$(mktemp /tmp/hook-XXXXXXXX)
    echo "${script}" > "${hook}"
    env BASH_ENV="${hook}" bash -c "${command}"
}


ln -s /usr/local/bin/bash /bin/bash &> /dev/null || true