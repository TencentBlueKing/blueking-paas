### Description

List gateway API permission apply records with system API credentials.

#### 1. Path parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| app_code | string | Yes | Application ID, must be managed by the caller |

#### 2. Query parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| applied_by | string | No | Applicant |
| applied_time_start | integer | No | Apply start time (Unix timestamp) |
| applied_time_end | integer | No | Apply end time (Unix timestamp) |
| apply_status | string | No | Apply status |
| query | string | No | Search keyword |
| limit | integer | No | Page size, defaults to 10 |
| offset | integer | No | Offset, defaults to 0 |

### Request example

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/cloudapi_v2/bkapps/applications/ai-demo/gateways/permissions/apply-records/?limit=10&offset=0
```

### Response example

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
            "apply_status_display": "Pending",
            "grant_dimension": "resource",
            "comment": "",
            "reason": "Need to call this API",
            "expire_days": 180,
            "gateway_name": "paasv3",
            "approval_url": "https://example.com/approval/12"
        }
    ]
}
```

### Response fields

| Field | Type | Description |
| --- | --- | --- |
| count | integer | Total count |
| results | list | Apply records |
| results[].id | integer | Apply record ID |
| results[].bk_app_code | string | Application ID |
| results[].applied_by | string | Applicant |
| results[].applied_time | string | Applied time |
| results[].handled_by | list | Approvers |
| results[].handled_time | string | Handled time, empty when pending |
| results[].apply_status | string | Apply status |
| results[].apply_status_display | string | Display text of apply status |
| results[].grant_dimension | string | Grant dimension: api / resource |
| results[].comment | string | Approval comment |
| results[].reason | string | Apply reason |
| results[].expire_days | integer | Requested validity in days |
| results[].gateway_name | string | Gateway name |
| results[].approval_url | string | Approval ticket link |
