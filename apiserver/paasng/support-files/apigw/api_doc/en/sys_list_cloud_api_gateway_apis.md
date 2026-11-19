### Description

List the applicable APIs of a gateway with system API credentials, including the permission status of the application.

#### Path parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| app_code | string | Yes | Application ID, must be managed by the caller |
| gateway_name | string | Yes | Gateway name |

### Request example

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/cloudapi_v2/bkapps/applications/ai-demo/gateways/paasv3/permissions/resources/
```

### Response example

```json
[
    {
        "id": 1,
        "name": "create_app",
        "gateway_name": "paasv3",
        "gateway_id": 1,
        "description": "Create application",
        "description_en": "Create application",
        "expires_in": null,
        "permission_level": "resource",
        "permission_status": "need_apply",
        "permission_action": "apply",
        "doc_link": "https://example.com/docs"
    }
]
```

### Response fields

| Field | Type | Description |
| --- | --- | --- |
| id | integer | Resource ID |
| name | string | API name |
| gateway_name | string | Gateway name |
| gateway_id | integer | Gateway ID |
| description | string | API description |
| description_en | string | English description |
| expires_in | integer | Remaining validity in seconds, null means unlimited |
| permission_level | string | Permission level |
| permission_status | string | Permission status of the application |
| permission_action | string | Available action (apply / renew) |
| doc_link | string | API document link |
