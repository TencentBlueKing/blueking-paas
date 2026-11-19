### Description

Apply gateway API permission with system API credentials.

#### Path parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| app_code | string | Yes | Application ID, must be managed by the caller |
| gateway_name | string | Yes | Gateway name |

#### Request body

```json
{
    "resource_ids": [1, 2],
    "reason": "Need to call this API",
    "expire_days": 180,
    "grant_dimension": "resource",
    "operator": "admin"
}
```

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| resource_ids | list[int] | No | Resource ID list; if empty, apply for the whole gateway |
| reason | string | No | Apply reason, up to 512 characters |
| expire_days | integer | Yes | Validity period in days |
| grant_dimension | string | Yes | Grant dimension: api / resource |
| operator | string | Yes | Operator username, recorded in PaaS audit log, virtual accounts allowed |

### Request example

```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -d '{"resource_ids": [1, 2], "reason": "Need to call this API", "expire_days": 180, "grant_dimension": "resource", "operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/cloudapi_v2/bkapps/applications/ai-demo/gateways/paasv3/permissions/apply/
```

### Response example

```json
{
    "record_id": 12
}
```

### Response fields

| Field | Type | Description |
| --- | --- | --- |
| record_id | integer | Apply record ID, can be used to query the apply status |
