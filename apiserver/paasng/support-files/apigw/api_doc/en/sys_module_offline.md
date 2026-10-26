### Function Description

Take an AI Agent application module offline from the specified environment using application credentials. The caller must have the AIDEV system role, and the target application must be an AI Agent application, otherwise 403 is returned.

The offline logic is the same as the user-facing API `module_offline`. Only the operator is specified by the `operator` field in the request body. The `operator` is only recorded as the operator; its application permissions are not checked, and the environment deployment role protection does not apply.

### Request Parameters

#### 1. Path Parameters

| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code | string | Yes | Application ID. Must be an AI Agent application |
| module | string | Yes | Module name, e.g., "default" |
| env | string | Yes | Environment name, available values: "stag" / "prod" |

#### 2. Interface Parameters

| Field | Type | Required | Description |
| ------- | ------ | ---------- | ------------- |
| operator | string | Yes | Username of the operator, only used for recording. Virtual accounts are allowed. |

### Request Example

```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -d '{"operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/envs/stag/offlines/
```

### Response Example

```json
{
    "offline_operation_id": "22d0e9c8-9cfc-45a5-b5a8-718137c515db"
}
```

### Response Parameter Description

| Field | Type | Description |
| ------- | ------ | ------------- |
| offline_operation_id | string | Offline operation ID |
