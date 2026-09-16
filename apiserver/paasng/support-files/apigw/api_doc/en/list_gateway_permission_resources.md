### Function Description
List resources of a gateway and the current application's permission status for each resource.

`permission_status` is `owned` / `need_apply` / `pending` / `expired` / `rejected`. `permission_action` is `apply` / `renew`. Filter `need_apply` before applying, or `permission_action=renew` before renewing.

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code | string | Yes | Application ID, e.g. "appid1" |
| gateway_name | string | Yes | Gateway name, e.g. "paasv3", from `list_gateways` |

#### 2. Query Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| keyword | string | No | Resource name keyword |

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/paasv3/permissions/resources/?keyword=deploy'
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
        "expires_in": null,
        "permission_level": "normal",
        "permission_status": "need_apply",
        "permission_action": "apply",
        "doc_link": ""
    }
]
```

### Response Fields
| Field | Type | Description |
| ----- | ---- | ----------- |
| id | int | Resource ID, used as `resource_ids` when applying or renewing |
| name | string | Resource name |
| gateway_name | string | Gateway name |
| gateway_id | int | Gateway ID |
| description | string | Resource description |
| description_en | string | Resource description in English |
| expires_in | int | Remaining seconds; may be null when not owned or granted permanently |
| permission_level | string | Permission level: unlimited / normal / sensitive / special |
| permission_status | string | Status: owned / need_apply / pending / expired / rejected |
| permission_action | string | Next action: apply / renew |
| doc_link | string | Documentation link |

**Status Code Explanation:**
- **200**: Success
