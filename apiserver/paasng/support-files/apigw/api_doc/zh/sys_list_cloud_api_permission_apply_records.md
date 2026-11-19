### 功能描述

以应用身份查询网关接口权限申请记录，用于获取申请状态。

#### 1、路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| --- | --- | --- | --- |
| app_code | string | 是 | 应用 ID，必须归调用方管理 |

#### 2、接口参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| --- | --- | --- | --- |
| applied_by | string | 否 | 申请人 |
| applied_time_start | integer | 否 | 申请开始时间（Unix 时间戳） |
| applied_time_end | integer | 否 | 申请截止时间（Unix 时间戳） |
| apply_status | string | 否 | 申请状态 |
| query | string | 否 | 搜索关键字 |
| limit | integer | 否 | 每页条数，默认 10 |
| offset | integer | 否 | 偏移量，默认 0 |

### 请求示例

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/cloudapi_v2/bkapps/applications/ai-demo/gateways/permissions/apply-records/?limit=10&offset=0
```

### 返回结果示例

```json
{
    "count": 1,
    "results": [
        {
            "id": 12,
            "bk_app_code": "ai-demo",
            "applied_by": "admin",
            "applied_time": "2026-01-01 10:00:00",
            "handled_by": ["admin"],
            "handled_time": null,
            "apply_status": "pending",
            "apply_status_display": "待审批",
            "grant_dimension": "resource",
            "comment": "",
            "reason": "需要调用该接口",
            "expire_days": 180,
            "gateway_name": "paasv3",
            "approval_url": "https://example.com/approval/12"
        }
    ]
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| count | integer | 总条数 |
| results | list | 申请记录列表 |
| results[].id | integer | 申请记录 ID |
| results[].bk_app_code | string | 申请应用 ID |
| results[].applied_by | string | 申请人 |
| results[].applied_time | string | 申请时间 |
| results[].handled_by | list | 审批人列表 |
| results[].handled_time | string | 审批时间，未处理时为空 |
| results[].apply_status | string | 申请状态 |
| results[].apply_status_display | string | 申请状态展示文案 |
| results[].grant_dimension | string | 授权维度：api / resource |
| results[].comment | string | 审批备注 |
| results[].reason | string | 申请原因 |
| results[].expire_days | integer | 申请的有效期（天） |
| results[].gateway_name | string | 网关名称 |
| results[].approval_url | string | 审批单据链接 |
