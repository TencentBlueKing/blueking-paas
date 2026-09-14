### 功能描述
申请指定网关的资源权限，不支持跨网关。提交后返回申请记录 ID，可用 `list_resource_permission_apply_records` 或 `retrieve_resource_permission_apply_record` 查询审批结果。

推荐流程：
1. `list_gateways` 确认网关
2. `list_gateway_permission_resources` 拿到待申请资源的 `id`
3. `check_is_allowed_apply_by_gateway` 决定 `grant_dimension`
4. 调用本接口提交申请

按资源申请：`grant_dimension=resource`，并传入 `resource_ids`。按网关申请：`grant_dimension=api`，`resource_ids` 传空数组，且必须先确认允许按网关申请。

### 请求参数

#### 1、路径参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string | 是 | 应用 ID，如 "appid1" |
| gateway_name | string | 是 | 网关名称，如 "paasv3" |

#### 2、接口参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| grant_dimension | string | 是 | 授权维度：resource=按资源，api=按整个网关 |
| expire_days | int | 是 | 有效期：0=永久，180=6个月，360=12个月 |
| resource_ids | array[int] | 否 | 资源 ID 列表，来自 `list_gateway_permission_resources`。按网关申请时传空数组 |
| reason | string | 否 | 申请原因，最长 512 字符 |

### 请求示例
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{"grant_dimension":"resource","expire_days":180,"resource_ids":[123,456],"reason":"部署时需要调用 paasv3 接口"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/paasv3/permissions/apply/
```

### 返回结果示例
```json
{
    "record_id": 1001
}
```

### 返回结果参数说明
| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| record_id | int | 申请记录 ID |

**状态码说明：**
- **200**：提交成功
- **400**：参数不合法，例如按网关申请但该网关不允许，或 `expire_days` / `grant_dimension` 取值错误
