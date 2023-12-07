# cnb-builder-shim
蓝鲸 SaaS Builder shim, 提供在容器内运行 SaaS Builder 的能力。

# 使用说明

cnb-builder-shim 是一个运行在 cloudnative builder 之上的衬垫层，目前支持在 [heroku-builder](../cloudnative-buildpacks/builders/heroku-builder) 中使用。未来我们计划扩展其支持的基础镜像，例如 [paketo-builder](../cloudnative-buildpacks/builders/paketo-builder)。

## 1. 构建镜像

```bash
# 构建基于 heroku-builder 的镜像, 默认镜像名是
❯ make heroku-builder
# 可以通过环境变量指定镜像名称和 tag
❯ BUILDER_IMAGE_NAME="builder-heroku-bionic" BUILDER_IMAGE_TAG="latest" IMAGE_NAME="bk-builder-heroku-bionic" IMAGE_TAG="latest" make heroku-builder
```

## 2. 构建 SaaS 镜像

```bash
# 压缩源码成 tar 归档包
❯ tar -czvf source.tgz -C {源码目录} .
# 启动 Builder 构建镜像
❯ docker run --rm \
    # TODO: 修改成你需要构建的镜像名
    -e OUTPUT_IMAGE="mirrors.tencent.com/foo:latest" \
    -e RUN_IMAGE="mirrors.tencent.com/bkpaas/run-heroku-bionic:latest" \
    -e SOURCE_GET_URL="file:///tmp/source.tgz" \
    # 设置需要使用的 builderpack
    -e REQUIRED_BUILDPACKS="tgz fagiani/apt ... 0.2.5;tgz bk-buildpack-python ... v213" \
    # TODO: 修改成你的镜像源访问凭证, 结构为 Dict[str, str], key 是镜像仓库名称, value 是 Basic Auth 格式的用户凭证
    -e CNB_REGISTRY_AUTH='{"mirrors.tencent.com":"Basic YQ=="}' \
    # TODO: 修改 source 路径为你本地的应用源码
    --mount type=bind,source="$(pwd)"/source.tgz,target=/tmp/source.tgz \
    mirrors.tencent.com/bkpaas/heroku-builder-all-in-one:bionic
```