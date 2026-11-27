### Function Description

Take an application module offline from the specified environment using application credentials. The caller must have the AIDEV or AppSpark system role and can only operate on the applications it manages, otherwise 403 is returned:

- AIDEV: the target application must be an AI Agent application
- AppSpark: the source origin of the target application's default module must still be AppSpark, only the default module can be operated on (other modules return 403), and `env` must be prod; passing stag returns 400

The offline logic is the same as the user-facing API `module_offline`. Only the operator is specified by the `operator` field in the request body. The `operator` is only recorded as the operator; its application permissions are not checked, and the environment deployment role protection does not apply.

### Request Parameters

#### 1. Path Parameters

| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code | string | Yes | Application ID. Must be an application managed by the caller |
| module | string | Yes | Module name, e.g., "default" |
| env | string | Yes | Environment name, available values: "stag" / "prod". AppSpark can only pass "prod" |

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

If the environment is already offline, no new operation is created and the ID of the latest successful offline operation is returned.

### Error Description

| HTTP Status Code | Error Code | Scenario |
| ------ | ------ | ------ |
| 400 | OFFLINE_ENV_NOT_DEPLOYED | The environment has never been deployed, there is nothing to take offline |
| 400 | OFFLINE_ALREADY_IN_PROGRESS | An offline operation is already running in the environment |
| 400 | CANNOT_OFFLINE_APP | Offline failed for other reasons |
| 400 | SYSAPI_ENV_NOT_ALLOWED | The caller is not allowed to operate on the environment (e.g. AppSpark passing stag) |
| 403 | AI_AGENT_APP_REQUIRED / APP_SPARK_APP_REQUIRED / APP_SPARK_MODULE_REQUIRED | The application or module is not managed by the caller |
