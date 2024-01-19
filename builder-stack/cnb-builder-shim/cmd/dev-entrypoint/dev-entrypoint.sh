#!/bin/bash

DEVCONTAINER_DIR="/cnb/devcontainer"

function update_deploy_result() {
  echo $1 > $2
}

function hot_reload(){
  $DEVCONTAINER_DIR/bin/lifecycle-driver 2>&1 | tee $DEVCONTAINER_DIR/deploy/log/$1.log
  update_deploy_result ${PIPESTATUS[0]} $DEVCONTAINER_DIR/deploy/$1
}

function entrypoint() {
  # do dev-init
  $DEVCONTAINER_DIR/bin/dev-init
  # start devserver
  $DEVCONTAINER_DIR/bin/devserver &

  mkdir -p $DEVCONTAINER_DIR/src $DEVCONTAINER_DIR/deploy/log

  CODE_SRC_DIR=${UPLOAD_DIR:-"$DEVCONTAINER_DIR/src/"}
  inotifywait -e create -m -r $DEVCONTAINER_DIR/deploy/ --exclude '/\.' --exclude 'log/' | while read file; do
      # extract filename from $file. $file like "/cnb/devcontainer/deploy/ CREATE 17b270b8f189359eb2895768bf34f6a6"
      deploy_id=$(echo "$file" | awk '{print $NF}')
      hot_reload $deploy_id

      rm -f $CODE_SRC_DIR/*
  done
}

entrypoint
