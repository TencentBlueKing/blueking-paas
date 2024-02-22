一个应用模块可以同时启用多个进程，比如 web、worker 等。你可以通过源码仓库中的 `app_desc.yaml` 文件，来完成进程配置。

#### 1. 操作说明

打开位于项目根目录中的 `app_desc.yaml` 文件（如不存在请新建），修改 `module.processes` 字段来配置进程。

一份示例文件如下所示，其中定义了两个进程：`web` 和 `worker`：

```yaml
spec_version: 2
module:
  language: Python
  processes:
    web:
      command: gunicorn wsgi -w 4 -b [::]:${PORT}
    worker:
      command: celery -A app -l info
```

`processes` 字段的键为进程名称，值为进程详情。其中，`command` 是进程的启动命令，其支持使用 `${VAR_NAME}` 来引用环境变量。

每次修改 `app_desc.yaml` 后，你需要将改动推送到代码仓库并**重新部署模块**，这样新的进程配置才能生效。

#### 注意事项

1. 进程名称要求：以小写字母或数字开头，可包含小写字母、数字和中划线（`-`），不超过 12 个字符。
2. 如果模块设置了特殊的“构建目录”，那么 `app_desc.yaml` 文件就需要存放于该目录中，而非仓库根目录。

> 拓展阅读：[应用进程介绍](PROCFILE_DOC) | [应用描述文件](APP_DESC_DOC)
