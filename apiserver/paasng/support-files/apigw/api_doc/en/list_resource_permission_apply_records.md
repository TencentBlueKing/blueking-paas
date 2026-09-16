### Function Description
List gateway resource permission apply records. Use it to check whether an apply is approved. The `record_id` from `apply_gateway_resource_permission` can be passed to `retrieve_resource_permission_apply_record` for details.

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code | string | Yes | Application ID, e.g. "appid1" |

#### 2. Query Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| applied_by | string | No | Applicant |
| applied_time_start | int | No | Apply start time, Unix timestamp |
| applied_time_end | int | No | Apply end time, Unix timestamp |
| apply_status | string | No | Apply status: pending / approved / rejected / partial_approved |
| query | string | No | Search keyword |
| limit | int | No | Page size, default 10 |
| offset | int | No | Page offset, default 0 |

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/permissions/apply-records/?apply_status=pending&limit=10&offset=0'
```

### Response Example
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
            "apply_status_display": "Pending",
            "grant_dimension": "resource",
            "comment": "",
            "reason": "Need paasv3 APIs for deployment",
            "expire_days": 180,
            "gateway_name": "paasv3"
        }
    ]
}
```

### Response Fields
| Field | Type | Description |
| ----- | ---- | ----------- |
| count | int | Total record count |
| results | array | Apply records |
| results[].id | int | Apply record ID |
| results[].bk_app_code | string | Applicant application ID |
| results[].applied_by | string | Applicant |
| results[].applied_time | string | Apply time |
| results[].handled_by | array | Approvers |
| results[].handled_time | string / null | Handle time; null when still pending |
| results[].apply_status | string | Status: pending / approved / rejected / partial_approved |
| results[].apply_status_display | string | Status display text |
| results[].grant_dimension | string | Grant dimension: resource / api |
| results[].comment | string | Approval comment |
| results[].reason | string | Apply reason |
| results[].expire_days | int | Requested validity in days |
| results[].gateway_name | string | Gateway name |

**Status Code Explanation:**
- **200**: Success
