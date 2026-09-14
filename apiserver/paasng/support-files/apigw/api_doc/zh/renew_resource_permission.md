### 功能描述
续期已有网关资源权限，支持跨网关一次续期多个资源。`resource_ids` 来自 `list_app_resource_permissions` 或 `list_gateway_permission_resources` 中 `permission_action=renew` 的资源。

### 请求参数

#### 1、路径参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string | 是 | 应用 ID，如 "appid1" |

#### 2、接口参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| resource_ids | array[int] | 是 | 需要续期的资源 ID 列表，最多 100 个 |
| expire_days | int | 是 | 续期有效期：0=永久，180=6个月，360=12个月 |

### 请求示例
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{"resource_ids":[123,456],"expire_days":180}' --insecure https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/permissions/renew/
```

### 返回结果示例

**状态码说明：**
- **200** / **204**：续期成功（可能无响应体）
- **400**：参数不合法，例如资源不可续期或 `expire_days` 取值错误
