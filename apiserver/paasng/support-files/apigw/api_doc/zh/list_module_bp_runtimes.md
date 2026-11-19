### 功能描述
查询应用模块在 buildpack 构建方式下可用的基础镜像，以及每个基础镜像可选的构建工具（buildpack）。

修改构建配置时，`bp_stack_name` 取本接口的 `image`，`buildpacks` 只能从同一项的 `buildpacks` 中选择。同一语言在不同基础镜像下 id 不同。

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
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/bp_runtimes/
```

### 返回结果示例
```json
[
    {
        "image": "cnb-heroku-builder-noble",
        "slugbuilder": {"id": 24, "name": "cnb-heroku-builder-noble", "display_name": "Ubuntu24", "description": "", "image": "mirrors.example.com/bkpaas/builder-heroku-noble", "tag": "v2.5.0"},
        "slugrunner": {"id": 24, "name": "cnb-heroku-builder-noble", "display_name": "Ubuntu24", "description": "", "image": "mirrors.example.com/bkpaas/run-heroku-noble", "tag": "v2.5.0"},
        "buildpacks": [
            {"id": 48, "language": "Aptfile", "name": "bk-buildpack-apt", "display_name": "apt", "description": ""},
            {"id": 54, "language": "Python", "name": "bk-buildpack-python", "display_name": "blueking/python", "description": ""}
        ]
    }
]
```

### 返回结果参数说明
| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| image | string | 基础镜像名，即构建配置中的 `bp_stack_name` |
| slugbuilder | object | 构建镜像信息，`display_name` 为控制台展示的名称 |
| slugrunner | object | 运行镜像信息 |
| buildpacks | list | 该基础镜像可选的构建工具 |
| buildpacks[].id | int | 构建工具 ID，用于构建配置的 `buildpacks[].id` |
| buildpacks[].language | string | 构建工具对应的语言 |
