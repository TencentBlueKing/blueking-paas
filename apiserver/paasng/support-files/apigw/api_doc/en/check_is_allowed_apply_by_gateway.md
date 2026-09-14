### Function Description
Check whether applying permission by the whole gateway is allowed.

When `allow_apply_by_gateway=true`, call `apply_gateway_resource_permission` with `grant_dimension=api` and an empty `resource_ids` array. Otherwise apply by resource (`grant_dimension=resource`).

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code | string | Yes | Application ID, e.g. "appid1" |
| gateway_name | string | Yes | Gateway name, e.g. "paasv3" |

#### 2. Query Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/paasv3/permissions/allow-apply-by-gateway/
```

### Response Example
```json
{
    "allow_apply_by_gateway": true,
    "reason": ""
}
```

### Response Fields
| Field | Type | Description |
| ----- | ---- | ----------- |
| allow_apply_by_gateway | boolean | Whether applying by the whole gateway is allowed |
| reason | string | Reason when it is not allowed |

**Status Code Explanation:**
- **200**: Success
