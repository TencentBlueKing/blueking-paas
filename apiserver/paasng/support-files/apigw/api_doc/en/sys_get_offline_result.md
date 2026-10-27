### Function Description

Query the offline result of an application using application credentials. The caller must have the AIDEV or AppSpark system role and can only query the applications it manages, otherwise 403 is returned: AIDEV can only query AI Agent applications, and AppSpark can only query applications whose default module's source origin is still AppSpark, and only offline tasks of the default module in the production environment.

The response is the same as the user-facing API `get_offline_result`.

### Request Parameters

#### 1. Path Parameters

| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code | string | Yes | Application ID. Must be an application managed by the caller |
| module | string | Yes | Module name, e.g., "default" |
| offline_operation_id | string | Yes | UUID of the offline task |

#### 2. Interface Parameters

None.

### Request Example

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/offlines/4e69986f-00e8-41ad-bef9-8ac82201ae07/result/
```

### Response Example

```json
{
    "id": "4e69986f-00e8-41ad-bef9-8ac82201ae07",
    "status": "successful",
    "operator": {
        "id": "0336c3a7948c4299b7",
        "username": "admin",
        "provider_type": 3,
        "avatar": ""
    },
    "created": "2024-08-19 11:30:26",
    "log": "offline succeeded.",
    "err_detail": null,
    "offline_operation_id": "4e69986f-00e8-41ad-bef9-8ac82201ae07",
    "environment": "stag",
    "repo": {
        "source_type": "ai_agent",
        "type": "package",
        "name": "0.0.5",
        "url": "",
        "revision": "0.0.5",
        "comment": ""
    }
}
```

### Response Parameter Description

| Field | Type | Description |
| ------ | ------ | ------ |
| id | string | UUID |
| status | string | Offline status, optional values: successful, failed, pending |
| operator | object | Operator |
| created | string | Created |
| log | string | Offline log |
| err_detail | string | Offline exception reason |
| offline_operation_id | string | Offline operation ID |
| environment | string | Environment name |
| repo | object | Repository information |
