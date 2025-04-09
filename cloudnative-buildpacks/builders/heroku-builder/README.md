# heroku-builder

蓝鲸 SaaS Builder，用于将云原生应用从源代码构建成可运行镜像，基于 [heroku/base-images](https://github.com/heroku/base-images/tree/main) 项目。

## 开发指南

### 名词解释

- CNB Stack：基础镜像，用于构建 cnb builder / runner 等
- CNB builder：构建器镜像，可使用若干 buildpack 将源代码构建成可运行镜像

### 前置依赖

构建 cnb builder 需要安装 [pack](https://buildpacks.io/docs/tools/pack/)

### heroku-18（bionic）

基础镜像：[heroku-18 / ubuntu-bionic](https://github.com/heroku/stack-images/tree/v23/heroku-18) 

### 构建 cnb stack（基础镜像）

```bash
❯ make stack-bionic
# 可以通过环境变量指定镜像名称和 tag
❯ BUILD_IMAGE_NAME="build-heroku-bionic" STACK_BUILDER_TAG="latest" RUN_IMAGE_NAME="run-heroku-bionic" STACK_RUNNER_TAG="latest" make stack-bionic
```

### 构建 cnb builder（构建阶段镜像）

```bash
❯ make builder-bionic
# 可以通过环境变量指定镜像名称和 tag
# 如需修改基础镜像, 需要修改 heroku-18.toml 中的 run-image 和 build-image 字段
❯ BUILDER_IMAGE_NAME="builder-heroku-bionic" BUILDER_TAG="latest" make builder-bionic
```