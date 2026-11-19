### 功能描述
查看应用模块当前的构建配置。返回字段随构建方式不同：buildpack 返回基础镜像与构建工具，dockerfile 返回 Dockerfile 路径与构建参数，custom_image 返回镜像仓库。

修改构建配置前应先调用本接口，在返回结果上修改后再调用 `update_module_build_config`。

### 请求参数

#### 1、路径参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string | 是 | 应用 ID，如 "appid1" |
| module | string | 是 | 模块名称，如 "default" |

#### 2、接口参数：
暂无。

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/build_config/
```

### 返回结果示例
```json
{
    "build_method": "buildpack",
    "tag_options": {"prefix": null, "with_version": true, "with_build_time": true, "with_commit_id": false},
    "bp_stack_name": "cnb-heroku-builder-noble",
    "buildpacks": [
        {"id": 54, "language": "Python", "name": "bk-buildpack-python", "display_name": "blueking/python", "description": "蓝鲸 Python 云原生构建包"}
    ],
    "dockerfile_path": null,
    "docker_build_args": null,
    "env_image_repositories": {"stag": "mirrors.example.com/bkapps/appid1/default", "prod": "mirrors.example.com/bkapps/appid1/default"},
    "image_repository": null,
    "image_credential_name": null,
    "use_bk_ci_pipeline": false
}
```

### 返回结果参数说明
| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| build_method | string | 构建方式：buildpack / dockerfile / custom_image |
| tag_options | object | 镜像 Tag 规则 |
| bp_stack_name | string | buildpack 方式的基础镜像名 |
| buildpacks | list | buildpack 方式按顺序生效的构建工具 |
| dockerfile_path | string | Dockerfile 路径 |
| docker_build_args | object | Docker 构建参数 |
| env_image_repositories | object | 源码构建产出镜像的仓库地址 |
| image_repository | string | custom_image 方式的镜像仓库 |
| image_credential_name | string | custom_image 方式的镜像凭证名称 |
| use_bk_ci_pipeline | boolean | 是否通过蓝盾流水线构建 |
