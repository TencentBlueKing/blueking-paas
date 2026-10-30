
# kubectl exec 进入的交互式 bash 不经过 launcher，缺少应用环境。这里经 launcher 重新拉起 bash，并回到原来的工作目录。
# launcher 会从子进程环境中移除 CNB_PLATFORM_API，以此判断当前 shell 是否已经由 launcher 启动，避免重复拉起。
# 只传一个参数，launcher 会将其作为脚本交给 bash 执行，因此目录需要先转义。
if [[ $- == *i* && -n "$CNB_PLATFORM_API" && -x /cnb/lifecycle/launcher ]]; then
    exec /cnb/lifecycle/launcher "cd $(printf %q "$PWD") && exec bash"
fi
