### Function Description
List gateway resource permissions already granted to the current application. Use it to avoid duplicate applies, or to find resources that need renewal.

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code | string | Yes | Application ID, e.g. "appid1" |

#### 2. Query Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/permissions/app-permissions/
```

### Response Example
```json
[
    {
        "id": 123,
        "name": "deploy_with_module",
        "gateway_name": "paasv3",
        "gateway_id": 1,
        "description": "Deploy an app with module",
        "description_en": "Deploy an app with module",
        "expires_in": 15552000,
        "permission_level": "normal",
        "permission_status": "owned",
        "permission_action": "renew",
        "doc_link": ""
    }
]
```

### Response Fields
| Field | Type | Description |
| ----- | ---- | ----------- |
| id | int | Resource ID |
| name | string | Resource name |
| gateway_name | string | Gateway name |
| gateway_id | int | Gateway ID |
| description | string | Resource description |
| description_en | string | Resource description in English |
| expires_in | int | Remaining seconds; may be null for permanent grants |
| permission_level | string | Permission level: unlimited / normal / sensitive / special |
| permission_status | string | Status: owned / need_apply / pending / expired / rejected |
| permission_action | string | Next action: apply / renew |
| doc_link | string | Documentation link |

**Status Code Explanation:**
- **200**: Success
