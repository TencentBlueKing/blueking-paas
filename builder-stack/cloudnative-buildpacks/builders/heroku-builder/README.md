# cloudnative-buildpacks/builders/heroku-builder
蓝鲸 SaaS Builder, 基于 [heroku-18](https://github.com/heroku/stack-images/tree/v23/heroku-18) 镜像, 底层镜像是 ubuntu:bionic.

# 使用说明
## 1. 构建基础镜像 (stack)

```bash
❯ make stack-image
# 可以通过环境变量指定镜像名称和tag
❯ BUILD_IMAGE_NAME="build-heroku-bionic" STACK_BUILDER_TAG="latest" RUN_IMAGE_NAME="run-heroku-bionic" STACK_RUNNER_TAG="latest" make stack-image
```

## 2. 构建 cnb builder

前置依赖: 构建 cnb builder 需要安装 [pack](https://buildpacks.io/docs/tools/pack/)

```bash
❯ make builder
# 可以通过环境变量指定镜像名称和tag
# 如需修改基础镜像, 需要修改 builder.toml 中的 run-image 和 build-image 字段
❯ BUILDER_IMAGE_NAME="builder-heroku-bionic" BUILDER_TAG="latest" make builder
```