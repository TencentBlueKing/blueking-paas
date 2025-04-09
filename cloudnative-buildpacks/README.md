## 云原生 builder 镜像

### 开发说明

以下操作均在 `cloudnative-buildpacks` 目录下进行。

#### 构建 builder 基础镜像（heroku）

```bash
❯ cd builders/heroku-builder
❯ make builder-bionic
```

成功执行该命令后，将在本地生成一个名为 `mirrors.tencent.com/bkpaas/builder-heroku-bionic` 的 builder 镜像，其中打包了 `Python`、`Go` 和 `apt` 等多种 buildpack。流程细节如下：

1. 将 `buildpacks` 里的每个 buildpack 构建成镜像文件
2. 基于 `builder.toml` 配置文件，使用 `pack builder create` 命令创建出构建镜像
