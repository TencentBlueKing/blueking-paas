# smart-app-builder

smart-app-builder 是基于 cnb 方案， 专为蓝鲸 SaaS 设计的 S-Mart 包构建工具。它通过解析 SaaS 目录下的 app_desc.yaml 文件和源代码， 自动完成各模块的构建，并最终生成一个完整的 S-Mart 包。

## 使用方法

### 1. 准备依赖环境

[安装 Docker](https://docs.docker.com/engine/install/)

### 2. 构建 S-Mart 包

smart-app-builder 提供了两种构建环境，一种是 PIND(podman-in-docker)，另一种是 DIND(docker-in-docker)。

#### 2.1 基于 PIND 构建

执行以下命令，生成 `smart-app-builder:pind` 镜像

```
make build-pind-image
```

执行以下命令，构建 S-Mart 包

```
# 设置本地文件目录
export $APP_PATH='/data/home/app'
export $SMART_PATH='/data/home/smart'
# 运行构建命令
docker run -it --rm  --privileged \
    -e SOURCE_GET_URL=file:///podman/source \
    -e DEST_PUT_URL=file:///podman/dest \
    -e BUILDER_SHIM_IMAGE=bk-builder-heroku-bionic:v1.0.2 \
    -v $APP_PATH:/podman/source \
    -v $SMART_PATH:/podman/dest \
    smart-app-builder:pind
```

参数说明：
- `APP_PATH`: 当前主机上的源码存储目录。该目录将被挂载至容器内的 `/podman/source` 路径。为确保容器内用户 `podman（UID=1000，GID=1000）` 具有读写权限，可以执行 `chown -R 1000:1000 ${LOCAL_APP_PATH}`, 修改目录归属。
- `SMART_PATH`: 当前主机上 S-Mart 构建产物的存储目录。该目录将挂载至容器内的 `/podman/dest` 路径。需确保容器用户 `podman（UID=1000，GID=1000）` 具有读写权限。执行构建命令后，会在该目录下生成名为 `{app_code}.tgz` 的 S-Mart 包。
- `SOURCE_GET_URL`：源码目录的获取路径。由于 podman 采用了 rootless 模式运行，若 `SOURCE_GET_URL` 设置为本地文件目录(如示例中的 `/podman/source` )，则必须确保该目录对 `podman` 用户具有读写权限。
- `DEST_PUT_URL`: S-Mart 包的生成路径。同样地，`podman` 用户需要对目录具有读写权限(如示例中的 `/podman/dest`)。
- `BUILDER_SHIM_IMAGE`: CNB 构建工具镜像。镜像的制作方法可以参考 [cnb-builder-shim]([blueking-paas/cnb-builder-shim/README.md at builder-stack · TencentBlueKing/blueking-paas · GitHub](https://github.com/TencentBlueKing/blueking-paas/blob/builder-stack/cnb-builder-shim/README.md))。


#### 2.2 基于 DIND 构建

执行以下命令，生成 `smart-app-builder:dind` 镜像

```
make build-dind-image
```

执行以下命令，构建 S-Mart 包

```
# 设置本地文件目录
export $APP_PATH='/data/home/app'
export $SMART_PATH='/data/home/smart'
# 运行构建命令
docker run -it --rm  --privileged \
    -e SOURCE_GET_URL=file:///tmp/source \
    -e DEST_PUT_URL=file:///tmp/dest \
    -e BUILDER_SHIM_IMAGE=bk-builder-heroku-bionic:v1.0.2 \
    -v $APP_PATH:/tmp/source \
    -v $SMART_PATH:/tmp/dest \
    smart-app-builder:dind
```

参数说明：
- `APP_PATH`: 当前主机上的源码存储目录。该目录将被挂载至容器内的 `/tmp/source` 路径。
- `SMART_PATH`: 当前主机上 S-Mart 构建产物的存储目录。该目录将挂载至容器内的 `/podman/dest` 路径。执行构建命令后，会在该目录下生成名为` {app_code}.tgz` 的 S-Mart 包。
- `SOURCE_GET_URL`：源码目录的获取路径。
- `DEST_PUT_URL`: S-Mart 包的生成路径
- `BUILDER_SHIM_IMAGE`: CNB 构建工具镜像。镜像的制作方法可以参考 [cnb-builder-shim]([blueking-paas/cnb-builder-shim/README.md at builder-stack · TencentBlueKing/blueking-paas · GitHub](https://github.com/TencentBlueKing/blueking-paas/blob/builder-stack/cnb-builder-shim/README.md))。


### Buildpacks 环境配置
smart-app-builder 支持通过环境变量设置 buildpacks , 可在启动容器时通过 `docker run -e` 参数直接注入配置。

#### bk-buildpack-python
- `PYTHON_BUILDPACK_VERSION`: bk-buildpack-python 的版本。默认值 v213
- `PIP_VERSION`: pip 的版本。默认值 20.2.3
- `DISABLE_COLLECTSTATIC`: django 的 collectstatic 是否禁用。 默认值 1 表示禁用
- `BUILDPACK_S3_BASE_URL`: python 运行时版本的下载地址。默认值 https://bkpaas-runtimes-1252002024.file.myqcloud.com/python
- `PIP_INDEX_URL`: pip 的下载地址。默认值 https://mirrors.cloud.tencent.com/pypi/simple/
- `PIP_EXTRA_INDEX_URL`: pip 的第二个下载地址。默认值 https://mirrors.tencent.com/tencent_pypi/simple/

#### bk-buildpack-nodejs
- `NODEJS_BUILDPACK_VERSION`: bk-buildpack-nodejs 的版本。默认值 v163
- `S3_DOMAI`: node 运行时版本的下载地址。默认值 https://bkpaas-runtimes-1252002024.file.myqcloud.com/nodejs/node/release/linux-x64/
- `NPM_REGISTRY`: npm 的下载地址。默认值 https://mirrors.tencent.com/npm/

#### bk-buildpack-go
- `GO_BUILDPACK_VERSION`: bk-buildpack-go 的版本。默认值 v191
- `GO_BUCKET_URL`: go 运行时版本的下载地址。默认值 https://bkpaas-runtimes-1252002024.file.myqcloud.com/golang

#### bk-buildpack-apt
- `APT_BUILDPACK_VERSION`: bk-buildpack-apt 的版本。默认值 v2