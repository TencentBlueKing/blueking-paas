# cnb-builder-shim

蓝鲸 SaaS 云原生构建工具，提供在容器中基于源码构建 SaaS 镜像的能力。

本工具是一个运行在“云原生 builder 镜像”之上的“衬垫”层，其依赖一个有效的 builder 镜像，当前已支持 heroku builder，未来计划增加对 paketo builder 的支持。

## 开发说明

请先参考 [cloudnative-buildpacks/README.md](../cloudnative-buildpacks/README.md) 完成准备工作。

## 1. 构建镜像

执行以下命令构建新镜像：

```shell
make heroku-builder-bionic
```

其将使用默认的“云原生 builder 镜像”，名称为 `mirrors.tencent.com/bkpaas/builder-heroku-bionic:latest`，你也可以传递环境变量修改该默认名：

```shell
BUILDER_IMAGE_NAME="my-builder-heroku-bionic" BUILDER_IMAGE_TAG="my-tag" IMAGE_NAME="bk-builder-heroku-bionic" IMAGE_TAG="latest" make heroku-builder-bionic
```

- `BUILDER_IMAGE_*`：将要使用的“构建 builder 镜像”名称
- `IMAGE_*`：最终生成的镜像名称

## 使用示例

本构建工具直接被蓝鲸 PaaS 平台用于 SaaS 构建，因此，除了基本的镜像构建功能外，它还集成了镜像推送等功能。下面将简单演示工具的使用。

### 1. 准备工作

在项目根目录下的 `examples/python-flask` 中存放着一个简单的 Python Flask 应用，先将其打包成一个 `.tgz` 压缩包文件：

```bash
# 执行命令前，请切换至 builder-stack 根目录
tar -czvf /tmp/source.tgz -C examples/python-flask .
```

之后将用到 `/tmp/source.tgz` 文件。

本构建工具在往仓库推送镜像时需用到凭证信息，该信息可通过以下方式来生成：

```python
# 执行 python 命令进入交互式命令行

>>> import json, base64
# 替换代码中的相关信息：
# - registry.example.com：镜像仓库地址
# - username:password：用户名和密码
>>> auth = {'registry.example.com': 'Basic {}'.format(base64.b64encode(b'username:password').decode())}

>>> print(json.dumps(auth))
# 输出：<凭证信息>
```

将该凭证信息暂存起来，之后需要用到。

### 2. 将源码包构建为镜像

首先，通过环境变量设置一些关键参数：


```bash
# BUILDER_SHIM_IMAGE：构建工具镜像地址
export BUILDER_SHIM_IMAGE='mirrors.tencent.com/bkpaas/bk-builder-heroku-bionic:latest'
# OUTPUT_IMAGE：镜像推送的目标地址
export OUTPUT_IMAGE='mirrors.tencent.com/your_namespace/example-flask:latest'
# CNB_RUN_IMAGE：用于运行应用的基础镜像，需要可读权限
export CNB_RUN_IMAGE='mirrors.tencent.com/bkpaas/run-heroku-bionic:latest'
```

然后执行命令，将源码包构建为镜像：

```bash
docker run --rm \
    -e REQUIRED_BUILDPACKS="tgz bk-buildpack-apt ... v2;tgz bk-buildpack-python ... v213" \
    -e OUTPUT_IMAGE=$OUTPUT_IMAGE \
    -e CNB_RUN_IMAGE=$CNB_RUN_IMAGE \
    -e SOURCE_GET_URL="file:///tmp/source.tgz" \
    -e USE_DOCKER_DAEMON=true \
    --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
    --mount type=bind,source=/tmp/source.tgz,target=/tmp/source.tgz \
    $BUILDER_SHIM_IMAGE 
```

要点说明：

- 修改 `REQUIRED_BUILDPACKS` 来指定需要用到的 buildpacks
- 命令利用了 mount 将源码包 `/tmp/source.tgz` 挂载到了容器中并读取

## DevSandbox 的开发说明

基于 cnb-builder 框架，项目内提供了一种支持源码 hot-reload 的 dev sandbox 方案。

### 1. 构建镜像

执行以下命令构建新镜像：

```shell
make heroku-dev
```

其将使用默认的“云原生 builder 镜像”，名称为 `mirrors.tencent.com/bkpaas/builder-heroku-bionic:latest`，你也可以传递环境变量修改该默认名：

```shell
BUILDER_IMAGE_NAME="my-builder-heroku-bionic" BUILDER_IMAGE_TAG="my-tag" DEV_IMAGE_NAME="bk-dev-heroku-bionic" DEV_IMAGE_TAG="latest" make heroku-dev
```

- `DEV_IMAGE_NAME`: 目标开发镜像名
- `DEV_IMAGE_TAG`: 目标开发镜像 tag

### 2. 启动镜像
首先，通过环境变量设置一些关键参数。参数设置可选，仅当容器中默认的地址无效时，进行设置：

```shell
export PIP_INDEX_HOST="有效配置"
export PIP_INDEX_URL="有效配置"
export PIP_EXTRA_INDEX_URL="有效配置"
export BUILDPACK_S3_BASE_URL="有效配置"
```

执行命令, 启动开发容器

```shell
docker run -d --net=host \
    -e REQUIRED_BUILDPACKS="tgz bk-buildpack-apt ... v2;tgz bk-buildpack-python ... v213" \
    -e PIP_INDEX_HOST=$PIP_INDEX_HOST \
    -e PIP_INDEX_URL=$PIP_INDEX_URL \
    -e PIP_EXTRA_INDEX_URL=$PIP_EXTRA_INDEX_URL \
    -e BUILDPACK_S3_BASE_URL=$BUILDPACK_S3_BASE_URL \
    bk-dev-heroku-bionic:latest
```

### 3. 通过 http 请求完成源码的 hot-reload 
#### 3.1 请求源码部署

请求命令

```shell
# devsandbox_ip 替换成容器实际可访问的主机 IP
curl --location 'http://{devsandbox_ip}:8000/deploys' \
--header 'Authorization: Bearer xxx' \
--form 'file=@"django-helloworld.zip"'
```

结果示例

```json
{
    "deployID": "aaf79f28271e47bebf8448b63bddd04f"
}
```

#### 3.2 获取部署结果

请求命令

```shell
# devsandbox_ip 替换成容器实际可访问的主机 IP
# deployID 是上一步请求部署时返回的 deployID
curl --location 'http://{devsandbox_ip}:8000/deploys/{deployID}/results?log=true' --header 'Authorization: Bearer xxx'
```
结果示例

```json
{
    "log":"0 info  | 15:26:08.952363 | Starting builder... \n0 info  | 15:26:08.952393 | --> Detecting Buildpacks... \n..."
    "status": "Success"
}
```
