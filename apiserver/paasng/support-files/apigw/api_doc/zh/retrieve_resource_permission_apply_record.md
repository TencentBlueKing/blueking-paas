### 功能描述
获取网关资源权限申请记录详情，含本次申请的资源及各资源审批结果。`record_id` 来自 `apply_gateway_resource_permission` 或 `list_resource_permission_apply_records`。

### 请求参数

#### 1、路径参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string | 是 | 应用 ID，如 "appid1" |
| record_id | int | 是 | 申请记录 ID |

#### 2、接口参数：
暂无。

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/permissions/apply-records/1001/
```

### 返回结果示例
```json
{
    "id": 1001,
    "bk_app_code": "appid1",
    "applied_by": "admin",
    "applied_time": "2024-03-15 12:00:00",
    "handled_by": ["admin"],
    "handled_time": "2024-03-15 12:10:00",
    "apply_status": "approved",
    "apply_status_display": "通过",
    "grant_dimension": "resource",
    "comment": "",
    "reason": "部署时需要调用 paasv3 接口",
    "expire_days": 180,
    "gateway_name": "paasv3",
    "resources": [
        {
            "name": "deploy_with_module",
            "apply_status": "approved"
        }
    ]
}
```

### 返回结果参数说明
| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| id | int | 申请记录 ID |
| bk_app_code | string | 申请的应用 ID |
| applied_by | string | 申请人 |
| applied_time | string | 申请时间 |
| handled_by | array | 审批人 |
| handled_time | string / null | 处理时间，待审批时为 null |
| apply_status | string | 申请状态：pending / approved / rejected / partial_approved |
| apply_status_display | string | 申请状态展示文案 |
| grant_dimension | string | 授权维度：resource / api |
| comment | string | 审批意见 |
| reason | string | 申请原因 |
| expire_days | int | 申请的有效期天数 |
| gateway_name | string | 网关名称 |
| resources | array | 本次申请的资源列表 |
| resources[].name | string | 资源名称 |
| resources[].apply_status | string | 该资源的审批状态 |

**状态码说明：**
- **200**：查询成功
- **404**：申请记录不存在
