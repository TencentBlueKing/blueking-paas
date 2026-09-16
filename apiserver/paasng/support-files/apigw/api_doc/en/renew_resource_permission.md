### Function Description
Renew granted gateway resource permissions. Resources from different gateways can be renewed in one request. Take `resource_ids` from `list_app_resource_permissions` or from `list_gateway_permission_resources` items whose `permission_action` is `renew`.

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code | string | Yes | Application ID, e.g. "appid1" |

#### 2. Body Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| resource_ids | array[int] | Yes | Resource IDs to renew, max 100 |
| expire_days | int | Yes | Renewed validity: 0=permanent, 180=6 months, 360=12 months |

### Request Example
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{"resource_ids":[123,456],"expire_days":180}' --insecure https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/permissions/renew/
```

### Response Example

**Status Code Explanation:**
- **200** / **204**: Renewed successfully (response body may be empty)
- **400**: Invalid parameters, e.g. the resource cannot be renewed or `expire_days` is invalid
