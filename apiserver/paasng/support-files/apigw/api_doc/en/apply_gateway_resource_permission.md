### Function Description
Apply for resource permissions of a gateway. Cross-gateway apply is not supported. The response contains an apply record ID; use `list_resource_permission_apply_records` or `retrieve_resource_permission_apply_record` to check approval status.

Recommended flow:
1. Call `list_gateways` to confirm the gateway
2. Call `list_gateway_permission_resources` to get resource `id`s
3. Call `check_is_allowed_apply_by_gateway` to decide `grant_dimension`
4. Call this API to submit the apply

Apply by resource: `grant_dimension=resource` with `resource_ids`. Apply by gateway: `grant_dimension=api` with an empty `resource_ids` array, and only after the gateway allows it.

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code | string | Yes | Application ID, e.g. "appid1" |
| gateway_name | string | Yes | Gateway name, e.g. "paasv3" |

#### 2. Body Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| grant_dimension | string | Yes | Grant dimension: resource / api |
| expire_days | int | Yes | Validity: 0=permanent, 180=6 months, 360=12 months |
| resource_ids | array[int] | No | Resource IDs from `list_gateway_permission_resources`. Pass an empty array when applying by gateway |
| reason | string | No | Apply reason, max 512 characters |

### Request Example
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{"grant_dimension":"resource","expire_days":180,"resource_ids":[123,456],"reason":"Need paasv3 APIs for deployment"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/paasv3/permissions/apply/
```

### Response Example
```json
{
    "record_id": 1001
}
```

### Response Fields
| Field | Type | Description |
| ----- | ---- | ----------- |
| record_id | int | Apply record ID |

**Status Code Explanation:**
- **200**: Submitted successfully
- **400**: Invalid parameters, e.g. applying by gateway is not allowed, or `expire_days` / `grant_dimension` is invalid
