# cloudnative-buildpacks/builders/heroku-builder

蓝鲸 SaaS Builder, 基于 [heroku-18](https://github.com/heroku/stack-images/tree/v23/heroku-18) 镜像, 底层镜像是 ubuntu:bionic.

## 使用说明

### 1. 构建基础镜像 (stack)

```bash
❯ make stack-bionic
# 可以通过环境变量指定镜像名称和 tag
❯ BUILD_IMAGE_NAME="build-heroku-bionic" STACK_BUILDER_TAG="latest" RUN_IMAGE_NAME="run-heroku-bionic" STACK_RUNNER_TAG="latest" make stack-bionic
```

### 2. 构建 cnb builder

前置依赖: 构建 cnb builder 需要安装 [pack](https://buildpacks.io/docs/tools/pack/)

```bash
❯ make builder-bionic
# 可以通过环境变量指定镜像名称和 tag
# 如需修改基础镜像, 需要修改 heroku-18.toml 中的 run-image 和 build-image 字段
❯ BUILDER_IMAGE_NAME="builder-heroku-bionic" BUILDER_TAG="latest" make builder-bionic
```