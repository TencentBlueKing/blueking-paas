### 功能描述
修改应用模块的构建配置。请求体会整体覆盖当前配置：先用 `get_module_build_config` 取得当前配置，只修改需要的字段后完整提交，`use_bk_ci_pipeline` 不传会被重置为 false。

- buildpack：必填 `tag_options`、`bp_stack_name`、`buildpacks`。`bp_stack_name` 取自 `list_module_bp_runtimes` 的 `image`；`buildpacks` 的 id 必须属于所选基础镜像，同一语言在不同基础镜像下 id 不同，切换基础镜像时需按语言重新选择；列表顺序即构建顺序。
- dockerfile：必填 `tag_options`、`docker_build_args`（可为空对象），并提供 `dockerfile_path`。
- custom_image：必填 `image_repository`。custom_image 与其他构建方式之间不能互相切换。

修改后需重新部署才生效。

### 请求参数

#### 1、路径参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string | 是 | 应用 ID，如 "appid1" |
| module | string | 是 | 模块名称，如 "default" |

#### 2、Body 参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| build_method | string | 是 | buildpack / dockerfile / custom_image |
| tag_options | object | 否 | 镜像 Tag 规则：prefix、with_version、with_build_time、with_commit_id |
| bp_stack_name | string | 否 | 基础镜像名 |
| buildpacks | list | 否 | 有序构建工具列表，元素为 `{"id": <int>}` |
| dockerfile_path | string | 否 | Dockerfile 路径 |
| docker_build_args | object | 否 | Docker 构建参数 |
| image_repository | string | 否 | 镜像仓库 |
| image_credential_name | string | 否 | 镜像凭证名称 |
| use_bk_ci_pipeline | boolean | 否 | 是否通过蓝盾流水线构建，默认 false |

### 请求示例
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{"build_method":"buildpack","tag_options":{"prefix":null,"with_version":true,"with_build_time":true,"with_commit_id":false},"bp_stack_name":"cnb-heroku-builder-noble","buildpacks":[{"id":54}],"use_bk_ci_pipeline":false}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/build_config/
```

### 返回结果示例
成功时返回 204，无响应体。

**状态码说明：**
- **204**：修改成功
- **400**：参数缺失、构建方式不支持切换或构建工具不存在
