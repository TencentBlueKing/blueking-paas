### 功能描述
获取当前应用已申请的网关资源权限列表，可用于申请前避免重复提交，或筛选需要续期的资源。

### 请求参数

#### 1、路径参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string | 是 | 应用 ID，如 "appid1" |

#### 2、接口参数：
暂无。

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/permissions/app-permissions/
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
        "expires_in": 15552000,
        "permission_level": "normal",
        "permission_status": "owned",
        "permission_action": "renew",
        "doc_link": ""
    }
]
```

### 返回结果参数说明
| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| id | int | 资源 ID |
| name | string | 资源名称 |
| gateway_name | string | 所属网关名称 |
| gateway_id | int | 所属网关 ID |
| description | string | 资源描述 |
| description_en | string | 资源英文描述 |
| expires_in | int | 剩余有效秒数，永久授权时可能为 null |
| permission_level | string | 权限级别：unlimited / normal / sensitive / special |
| permission_status | string | 权限状态：owned / need_apply / pending / expired / rejected |
| permission_action | string | 可执行操作：apply / renew |
| doc_link | string | 文档链接 |

**状态码说明：**
- **200**：查询成功
