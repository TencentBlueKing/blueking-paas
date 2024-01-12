#!/bin/sh

# do dev-init
/cnb/devcontainer/bin/dev-init

# start devserver
/cnb/devcontainer/bin/devserver &



mkdir -p /cnb/devcontainer/log



mkdir -p /cnb/process/
cd /cnb/process/
ln -s /lifecycle/launcher web

#supervisord -c /cnb/supervisor/dev.conf
#
## 监听某个文件变化即可，否则多个文件变化都会导致重启
#inotifywait -e modify,attrib,move,create,delete,delete_self,unmount -m -r /app/ --exclude '/\.' | while read file; do
#    echo $file
#    supervisorctl -c /cnb/supervisor/dev.conf update
#    supervisorctl -c /cnb/supervisor/dev.conf restart all
#done




while sleep 30; do
  echo "i am sleep ..."
done