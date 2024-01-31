通过定义“钩子命令”，你可以在部署过程中的一些特殊节点，触发执行一些特定命令。“钩子命令”适合用来完成环境初始化、数据库变更之类的工作。

#### 1. 配置“部署前置（pre_release）”钩子

“部署前置”钩子命令的执行时机是**构建完成后、发布进程前**。它很适合用来完成数据表结构变更等任务。

你需要修改 `app_desc.yaml` 文件中的 `module.scripts` 字段，来创建一个部署前置钩子。一份示例文件如下所示：

```yaml
spec_version: 2
module:
  language: Python
  scripts:
    pre_release_hook: "python manage.py migrate --no-input"
  processes:
	# ...已省略
```

#### 注意事项

1. 平台在执行“部署前置”钩子命令时，会使用一个全新容器，而非复用构建阶段的已有容器，因此，在构建期间对本地文件的任何变更，**不会**在钩子命令的执行环境中生效。

> 拓展阅读：[部署阶段钩子](DEPLOY_ORDER) | [构建阶段钩子](BUILD_PHASE_HOOK)


