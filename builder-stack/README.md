# 项目简介

## cnb-builder-shim
蓝鲸 SaaS Builder shim, 提供在容器内运行 SaaS Builder 的能力。

## kaniko-shim
蓝鲸 Docker Builder shim, 提供在容器内构建镜像的能力。

## cloudnative-buildpacks/builders/heroku-builder
蓝鲸 SaaS Builder, 基于 [heroku-18](https://github.com/heroku/stack-images/tree/v23/heroku-18) 镜像, 底层镜像是 ubuntu:bionic.

## cloudnative-buildpacks/builders/paketo-builder(WIP)
蓝鲸 SaaS Builder, 基于 [paketo-buildpacks/bionic-base-stack](https://github.com/paketo-buildpacks/bionic-base-stack), 底层镜像是 ubuntu:bionic.

## cloudnative-buildpacks/buildpacks/bk-buildpack-python
蓝鲸 SaaS(Python) 的构建工具, 基于 heroku-buildpack-python.

## cloudnative-buildpacks/buildpacks/bk-buildpack-nodejs
蓝鲸 SaaS(NodeJS) 的构建工具, 基于 heroku-buildpack-nodejs.

## cloudnative-buildpacks/buildpacks/bk-buildpack-go
蓝鲸 SaaS(Golang) 的构建工具, 基于 heroku-buildpack-go.

# 开发说明

## ⚠️ 注意事项
本项目使用了 submodule, 在执行 `make` 命令前, 请确保已初始化 submodule
```bash
❯ git submodule init
❯ git submodule update
# 或
❯ git submodule update --init
```

## 构建流程
### CloudNative Builder
1. 构建 buildpacks
```bash
❯ cd cloudnative-buildpacks/buildpacks
❯ make all
```

2. 构建 builder 基础镜像
```bash
❯ cd cloudnative-buildpacks/builders/heroku-builder
❯ make builder
```

3. 构建集成 cnb-builder-shim 的 builder 镜像
```bash
❯ cd cnb-builder-shim
❯ make heroku-builder
```

### Kaniko Builder
1. 构建继承 kaniko-shim 的 builder 镜像
```bash
❯ cd kaniko-shim
❯ make image
```

## 使用说明
`cnb-builder-shim` 和 `kaniko-shim` 的所有参数都通过环境变量传递, 构建镜像后, 只需要通过环境变量传递对应参数即可进行源码构建。

### CloudNative Builder

```bash
# 压缩源码成 tar 归档包
❯ tar -czvf source.tgz -C {源码目录} .
# 启动 Builder 构建镜像
❯ docker run --rm \
    # TODO: 修改成你需要构建的镜像名
    -e OUTPUT_IMAGE="mirrors.tencent.com/foo:latest" \
    -e RUN_IMAGE="mirrors.tencent.com/bkpaas/heroku-stack-bionic:run" \
    -e SOURCE_GET_URL="file:///tmp/source.tgz" \
    -e REQUIRED_BUILDPACKS="tgz fagiani/apt ... 0.2.5;tgz blueking/python ... v213" \
    # 非必要不要改这个值
    -e CNB_PLATFORM_API="0.11" \
    # TODO: 修改成你的镜像源访问凭证, 结构为 Dict[str, str], key 是镜像仓库名称, value 是 Basic Auth 格式的用户凭证
    -e CNB_REGISTRY_AUTH='{"mirrors.tencent.com":"Basic YQ=="}' \
    # TODO: 修改 source 路径为你本地的应用源码
    --mount type=bind,source="$(pwd)"/source.tgz,target=/tmp/source.tgz \
    mirrors.tencent.com/bkpaas/heroku-builder-all-in-one:bionic
```

### Kaniko Builder

```bash
# 压缩构建上下文成 tar 归档包
❯ tar -czvf context.tgz -C {源码目录} .
# 启动 Builder 构建镜像
❯ docker run --rm \
    # TODO: 修改成你需要构建的镜像名
    -e OUTPUT_IMAGE="mirrors.tencent.com/foo:latest" \
    -e SOURCE_GET_URL="file:///tmp/source.tgz" \
    -e DOCKERFILE_PATH="Dockerfile" \
    # TODO: 修改成你的镜像源访问凭证, 值为 base64 编码后的 docker config json
    -e DOCKER_CONFIG_JSON='...' \
    # TODO: 修改 source 路径为你本地的应用源码
    --mount type=bind,source="$(pwd)"/source.tgz,target=/tmp/source.tgz \
    mirrors.tencent.com/bkpaas/kaniko-executor
```