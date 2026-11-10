### Description

List gateways with system API credentials.

#### Path parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| app_code | string | Yes | Application ID, must be managed by the caller |

### Request example

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/cloudapi_v2/bkapps/applications/ai-demo/gateways/
```

### Response example

```json
[
    {
        "id": 1,
        "name": "paasv3",
        "description": "PaaS platform gateway",
        "maintainers": ["admin"],
        "doc_maintainers": {}
    }
]
```

### Response fields

| Field | Type | Description |
| --- | --- | --- |
| id | integer | Gateway ID |
| name | string | Gateway name |
| description | string | Gateway description |
| maintainers | list | Maintainers |
| doc_maintainers | object | Document maintainers |
