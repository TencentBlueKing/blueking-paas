### Function Description
Get details of a gateway resource permission apply record, including the requested resources and each resource's approval result. `record_id` comes from `apply_gateway_resource_permission` or `list_resource_permission_apply_records`.

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code | string | Yes | Application ID, e.g. "appid1" |
| record_id | int | Yes | Apply record ID |

#### 2. Query Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/permissions/apply-records/1001/
```

### Response Example
```json
{
    "id": 1001,
    "bk_app_code": "appid1",
    "applied_by": "admin",
    "applied_time": "2024-03-15 12:00:00",
    "handled_by": ["admin"],
    "handled_time": "2024-03-15 12:10:00",
    "apply_status": "approved",
    "apply_status_display": "Approved",
    "grant_dimension": "resource",
    "comment": "",
    "reason": "Need paasv3 APIs for deployment",
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

### Response Fields
| Field | Type | Description |
| ----- | ---- | ----------- |
| id | int | Apply record ID |
| bk_app_code | string | Applicant application ID |
| applied_by | string | Applicant |
| applied_time | string | Apply time |
| handled_by | array | Approvers |
| handled_time | string / null | Handle time; null when still pending |
| apply_status | string | Status: pending / approved / rejected / partial_approved |
| apply_status_display | string | Status display text |
| grant_dimension | string | Grant dimension: resource / api |
| comment | string | Approval comment |
| reason | string | Apply reason |
| expire_days | int | Requested validity in days |
| gateway_name | string | Gateway name |
| resources | array | Resources in this apply |
| resources[].name | string | Resource name |
| resources[].apply_status | string | Approval status of this resource |

**Status Code Explanation:**
- **200**: Success
- **404**: Apply record not found
