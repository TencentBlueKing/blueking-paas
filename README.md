## 项目简介

本项目包含以下两个核心组件：

1. **云原生构建工具**：用于构建蓝鲸 SaaS 的构建工具（基于云原生 buildpack）, 提供在容器中构建 SaaS 的能力，其功能依赖一个有效的“云原生 builder 镜像”
    - 目录：`cnb-builder-shim`
2. **容器镜像构建工具**：用于构建蓝鲸 SaaS 的构建工具（基于 Dockerfile）, 提供在容器内基于 Dockerfile 文件来构建镜像的能力。
    - 目录：`kaniko-shim`

“云原生 builder 镜像”是基于 [pack](https://github.com/buildpacks/pack) 命令打包而成的构建镜像，其通过内嵌 buildpacks 来满足多种编程语言的构建需求。项目当前共实现了两种“builder 镜像”：

- **heroku**：基于 [heroku-18](https://github.com/heroku/stack-images/tree/v23/heroku-18) 镜像, 底层镜像是 ubuntu:bionic
    - 目录：`cloudnative-buildpacks/builders/heroku-builder`
- WIP：**paketo**：基于 [paketo-buildpacks/bionic-base-stack](https://github.com/paketo-buildpacks/bionic-base-stack) 的 builder 镜像，测试中，请勿使用。
    - 目录：`cloudnative-buildpacks/builders/paketo-builder`

其中，heroku builder 镜像所使用的 buildpack 在原有代码上做了一些改动，维护在 `heroku-buildpacks` 目录中：

- `bk-buildpack-python`：Python 语言, 基于 heroku-buildpack-python
- `bk-buildpack-nodejs`：Node.js 语言, 基于 heroku-buildpack-nodejs
- `bk-buildpack-go`：Go 语言, 基于 heroku-buildpack-go

## 开发说明

### ⚠️ 注意事项

本项目使用了 submodule, 在执行 `make` 命令前, 请确保已初始化 submodule

```bash
❯ git submodule init
❯ git submodule update
# 或
❯ git submodule update --init
```

安装必要的依赖工具：[pack](https://github.com/buildpacks/pack)。

### 云原生构建工具

请参考 [cnb-builder-shim/README.md](cnb-builder-shim/README.md)，依赖“云原生 builder 镜像”。

### 云原生 builder 镜像

请参考 [cloudnative-buildpacks/README.md](cloudnative-buildpacks/README.md)。

### 容器镜像构建工具（kaniko builder）

请参考 [kaniko-shim/README.md](kaniko-shim/README.md)。
