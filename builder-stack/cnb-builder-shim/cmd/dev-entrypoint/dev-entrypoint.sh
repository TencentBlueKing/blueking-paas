#!/bin/bash


function sync_src() {
  # $1 e.g "/cnb/devcontainer/src/ CREATE demo_api_project.zip"
  # $2 e.g "/cnb/devcontainer/src/"

  rm -rf /app/*

  filename=$(echo "$1" | awk '{print $NF}')
  unzip -o -q "$2$filename" -d /tmp

  folder_name=$(basename "$filename" .zip)
  mv /tmp/$folder_name/* /app/

  rm -rf /tmp/$folder_name

  echo "$2$filename sync done"
}


function entrypoint() {
    # do dev-init
    /cnb/devcontainer/bin/dev-init
    # start devserver
    /cnb/devcontainer/bin/devserver &

    mkdir -p /cnb/devcontainer/log /cnb/devcontainer/src /cnb/devcontainer/releases

    CODE_SRC_DIR=${UPLOAD_DIR:-"/cnb/devcontainer/src/"}

    inotifywait -e create -m -r $CODE_SRC_DIR --exclude '/\.' | while read file; do
        sync_src "$file" "$CODE_SRC_DIR"
        /cnb/devcontainer/bin/lifecycle-driver
    done
}


entrypoint
