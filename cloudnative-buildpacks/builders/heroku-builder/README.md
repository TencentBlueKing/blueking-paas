# cloudnative-buildpacks/builders/heroku-builder

蓝鲸 SaaS Builder, 基于 [heroku-24](https://github.com/heroku/base-images/tree/v149/heroku-24) 镜像, 底层镜像是 ubuntu:noble.

## 使用说明

### 1. 构建基础镜像 (stack)

基础镜像（Stack）基于 Ubuntu 镜像构建而来，将用于进一步构建成 cnb builder 镜像，亦可作为 runner 镜像使用

```bash
❯ make stack-noble
# 可以通过环境变量指定镜像名称和 tag
❯ BUILD_IMAGE_NAME="build-heroku-noble" STACK_BUILDER_TAG="latest" RUN_IMAGE_NAME="run-heroku-noble" STACK_RUNNER_TAG="latest" make stack-noble
```

### 2. 构建 cnb builder

cnb builder 由基础镜像（Stack）+ buildpacks 构建而来，可用于将源码包构建为可运行的 SaaS 镜像

前置依赖: 构建 cnb builder 需要安装 [pack](https://buildpacks.io/docs/tools/pack/)

```bash
❯ make builder-noble
# 可以通过环境变量指定镜像名称和 tag
# 如需修改基础镜像, 需要修改 heroku-24.toml 中的 run-image 和 build-image 字段
❯ BUILDER_IMAGE_NAME="builder-heroku-noble" BUILDER_TAG="latest" make builder-noble
```
