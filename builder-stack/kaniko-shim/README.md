# kaniko-shim

蓝鲸 Docker Builder Shim, 提供在容器内构建镜像的能力。

## 使用说明

kaniko-shim 的使用方式与 [kaniko](https://github.com/GoogleContainerTools/kaniko) 相似，但它通过环境变量来传递构建参数。
目前支持的环境变量如下:

| 环境变量名                 | 含义                                                               |
|----------------------------|------------------------------------------------------------------|
| DOCKERFILE_PATH            | 要构建的 dockerfile 的路径。                                             |
| BUILD_ARG                  | 此标志允许您在构建时传入 ARG 值。对于多个值，请用 `,` 连接；每个值应为 base64 编码的 k=v 对。       |
| OUTPUT_IMAGE               | kaniko 将创建的镜像名称。                                                 |
| CACHE_REPO                 | 指定一个用作缓存的仓库，否则将从提供的目标推断出一个；当以 `oci:` 为前缀时，仓库将以 OCI 镜像格式写入所提供的路径。 |
| SOURCE_GET_URL             | dockerfile 构建上下文的网址                                              |
| DOCKER_CONFIG_JSON         | 访问容器镜像仓库的 Docker 凭据。                                             |
| INSECURE_REGISTRIES        | 使用纯 HTTP 推送和拉取的不安全仓库。用 `;` 连接多个仓库。                               |
| SKIP_TLS_VERIFY_REGISTRIES | 忽略 TLS 验证以推送和拉取的不安全仓库。用 `;` 连接多个仓库。                              |


## 开发说明

1. 构建继承 kaniko-shim 的 builder 镜像

```bash
❯ cd kaniko-shim
❯ make image
```

## 使用示例

`kaniko-shim` 的所有参数都通过环境变量传递, 构建镜像后, 只需要通过环境变量传递对应参数即可进行源码构建。

```bash
# 启动 Builder 构建镜像, 构建上下文是当前目录
❯ docker run --rm \
    # TODO: 修改成你需要构建的镜像名
    -e OUTPUT_IMAGE="mirrors.tencent.com/foo:latest" \
    -e SOURCE_GET_URL="dir:///tmp/source" \
    -e DOCKERFILE_PATH="Dockerfile" \
    # TODO: 修改成你的镜像源访问凭证, 值为 base64 编码后的 docker config json
    -e DOCKER_CONFIG_JSON='...' \
    --mount type=bind,source="$(pwd)",target=/tmp/source \
    mirrors.tencent.com/bkpaas/kaniko-executor
```