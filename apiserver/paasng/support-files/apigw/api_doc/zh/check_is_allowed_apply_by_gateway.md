### 功能描述
检查是否允许按整个网关申请资源权限。

`allow_apply_by_gateway=true` 时，调用 `apply_gateway_resource_permission` 可将 `grant_dimension` 设为 `api`，且 `resource_ids` 传空数组。否则只能按资源申请（`grant_dimension=resource`）。

### 请求参数

#### 1、路径参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string | 是 | 应用 ID，如 "appid1" |
| gateway_name | string | 是 | 网关名称，如 "paasv3" |

#### 2、接口参数：
暂无。

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/paasv3/permissions/allow-apply-by-gateway/
```

### 返回结果示例
```json
{
    "allow_apply_by_gateway": true,
    "reason": ""
}
```

### 返回结果参数说明
| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| allow_apply_by_gateway | boolean | 是否允许按整个网关申请 |
| reason | string | 不允许时的原因 |

**状态码说明：**
- **200**：查询成功
