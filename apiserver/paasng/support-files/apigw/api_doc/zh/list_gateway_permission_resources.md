### 功能描述
获取指定网关下的资源列表，以及当前应用对这些资源的权限状态。

`permission_status` 为 `owned` / `need_apply` / `pending` / `expired` / `rejected`；`permission_action` 为 `apply` / `renew`。申请前先筛出 `need_apply` 的资源，续期则筛 `permission_action=renew` 的资源。

### 请求参数

#### 1、路径参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string | 是 | 应用 ID，如 "appid1" |
| gateway_name | string | 是 | 网关名称，如 "paasv3"，来自 `list_gateways` |

#### 2、接口参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| keyword | string | 否 | 资源名称关键字 |

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/paasv3/permissions/resources/?keyword=deploy'
```

### 返回结果示例
```json
[
    {
        "id": 123,
        "name": "deploy_with_module",
        "gateway_name": "paasv3",
        "gateway_id": 1,
        "description": "App 部署（支持多模块）",
        "description_en": "Deploy an app with module",
        "expires_in": null,
        "permission_level": "normal",
        "permission_status": "need_apply",
        "permission_action": "apply",
        "doc_link": ""
    }
]
```

### 返回结果参数说明
| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| id | int | 资源 ID，申请/续期时作为 `resource_ids` 传入 |
| name | string | 资源名称 |
| gateway_name | string | 所属网关名称 |
| gateway_id | int | 所属网关 ID |
| description | string | 资源描述 |
| description_en | string | 资源英文描述 |
| expires_in | int | 剩余有效秒数，未拥有或永久授权时可能为 null |
| permission_level | string | 权限级别：unlimited / normal / sensitive / special |
| permission_status | string | 权限状态：owned=已拥有，need_apply=未申请，pending=申请中，expired=已过期，rejected=已拒绝 |
| permission_action | string | 可执行操作：apply=申请，renew=续期 |
| doc_link | string | 文档链接 |

**状态码说明：**
- **200**：查询成功
