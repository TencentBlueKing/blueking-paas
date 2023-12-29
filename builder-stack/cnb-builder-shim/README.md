# cnb-builder-shim

蓝鲸 SaaS 云原生构建工具，提供在容器中基于源码构建 SaaS 镜像的能力。

本工具是一个运行在“云原生 builder 镜像”之上的“衬垫”层，其依赖一个有效的 builder 镜像，当前已支持 heroku builder，未来计划增加对 paketo builder 的支持。

## 开发说明

请先参考 [../cloudnative-buildpacks/README.md](../cloudnative-buildpacks/README.md) 完成准备工作。

## 1. 构建镜像

执行以下命令构建新镜像：

    make heroku-builder

其将使用默认的“云原生 builder 镜像”，名称为 `mirrors.tencent.com/bkpaas/builder-heroku-bionic:latest`，你也可以传递环境变量修改该默认名：


    BUILDER_IMAGE_NAME="my-builder-heroku-bionic" BUILDER_IMAGE_TAG="my-tag" IMAGE_NAME="bk-builder-heroku-bionic" IMAGE_TAG="latest" make heroku-builder

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
# REGISTRY_AUTH：在前面的“准备工作”中生成的凭证信息
export REGISTRY_AUTH='{"mirros.tencent.com": "Basic ..."}'
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
    -e CNB_REGISTRY_AUTH="$REGISTRY_AUTH" \
    -e SOURCE_GET_URL="file:///tmp/source.tgz" \
    --mount type=bind,source=/tmp/source.tgz,target=/tmp/source.tgz \
    $BUILDER_SHIM_IMAGE 
```

要点说明：

- 修改 `REQUIRED_BUILDPACKS` 来指定需要用到的 buildpacks
- 命令利用了 mount 将源码包 `/tmp/source.tgz` 挂载到了容器中并读取
