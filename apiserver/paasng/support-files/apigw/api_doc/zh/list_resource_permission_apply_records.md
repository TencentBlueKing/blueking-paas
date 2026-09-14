### 功能描述
获取网关资源权限申请记录，可用于查询申请单是否通过。`apply_gateway_resource_permission` 返回的 `record_id` 可再配合 `retrieve_resource_permission_apply_record` 查看详情。

### 请求参数

#### 1、路径参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string | 是 | 应用 ID，如 "appid1" |

#### 2、接口参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| applied_by | string | 否 | 申请人 |
| applied_time_start | int | 否 | 申请开始时间，Unix 时间戳 |
| applied_time_end | int | 否 | 申请结束时间，Unix 时间戳 |
| apply_status | string | 否 | 申请状态：pending / approved / rejected / partial_approved |
| query | string | 否 | 搜索关键字 |
| limit | int | 否 | 分页大小，默认 10 |
| offset | int | 否 | 分页偏移，默认 0 |

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/permissions/apply-records/?apply_status=pending&limit=10&offset=0'
```

### 返回结果示例
```json
{
    "count": 1,
    "results": [
        {
            "id": 1001,
            "bk_app_code": "appid1",
            "applied_by": "admin",
            "applied_time": "2024-03-15 12:00:00",
            "handled_by": [],
            "handled_time": null,
            "apply_status": "pending",
            "apply_status_display": "待审批",
            "grant_dimension": "resource",
            "comment": "",
            "reason": "部署时需要调用 paasv3 接口",
            "expire_days": 180,
            "gateway_name": "paasv3"
        }
    ]
}
```

### 返回结果参数说明
| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| count | int | 总记录数 |
| results | array | 申请记录列表 |
| results[].id | int | 申请记录 ID |
| results[].bk_app_code | string | 申请的应用 ID |
| results[].applied_by | string | 申请人 |
| results[].applied_time | string | 申请时间 |
| results[].handled_by | array | 审批人 |
| results[].handled_time | string / null | 处理时间，待审批时为 null |
| results[].apply_status | string | 申请状态：pending / approved / rejected / partial_approved |
| results[].apply_status_display | string | 申请状态展示文案 |
| results[].grant_dimension | string | 授权维度：resource / api |
| results[].comment | string | 审批意见 |
| results[].reason | string | 申请原因 |
| results[].expire_days | int | 申请的有效期天数 |
| results[].gateway_name | string | 网关名称 |

**状态码说明：**
- **200**：查询成功
