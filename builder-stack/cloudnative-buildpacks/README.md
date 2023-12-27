## 云原生 builder 镜像

### 开发说明

以下操作均在 `cloudnative-buildpacks/builders/` 目录下进行。

1. 构建 buildpacks

```bash
❯ cd buildpacks
❯ make all
```

该命令使用 `pack` 命令将每个 buildpack 构建成镜像（输出为 `.cnb` 文件）。需注意的是，`buildpacks` 中的各文件夹中仅包含配置，实际的 buildpack 存放在项目根目录中的 `heroku-buildpacks` 中。

2. 构建 builder 基础镜像（heroku）

```bash
❯ cd heroku-builder
❯ make builder
```

成功执行该命令后，将在本地生成一个名为 `mirrors.tencent.com/bkpaas/builder-heroku-bionic` 的 builder 镜像，其中打包了 `Python`、`Go` 和 `apt` 等多种 buildpack。流程细节如下：

1. 将 `buildpacks` 里的每个 buildpack 构建成镜像文件（参考：“*1. 构建 buildpacks*”）
2. 基于 `builder.toml` 配置文件，使用 `pack builder create` 命令创建出构建镜像
