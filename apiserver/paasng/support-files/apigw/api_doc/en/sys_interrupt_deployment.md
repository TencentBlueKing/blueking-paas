### Function Description

Interrupt an ongoing deployment using application credentials. The caller must have the AIDEV or AppSpark system role and can only operate on the applications it manages, otherwise 403 is returned:

- AIDEV: the target application must be an AI Agent application
- AppSpark: the source origin of the target application's default module must still be AppSpark, and only deployments of the default module in the production environment can be interrupted (other modules return 403, and deployments in the staging environment return 400)

The interruption logic is the same as the user-facing API, except that `operator` does not have to be the user who started the deployment. The `operator` is only written to the application's operation records; its application permissions are not checked.

A successful response only means the interruption request has been accepted. It usually takes 1-5 seconds to take effect, so the caller should keep polling `sys_get_deployment_result` until the status becomes `interrupted`.

### Request Parameters

#### 1. Path Parameters

| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code | string | Yes | Application ID. Must be an application managed by the caller |
| module | string | Yes | Module name, e.g., "default" |
| deployment_id | string | Yes | Deployment task ID |

#### 2. Interface Parameters

| Field | Type | Required | Description |
| ------- | ------ | ---------- | ------------- |
| operator | string | Yes | Username of the user who requests the interruption, only written to the operation records. Virtual accounts are allowed. |

### Request Example

```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "app-spark", "bk_app_secret": "***"}' -d '{"operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/applications/demo-app/modules/default/deployments/22d0e9c8-9cfc-45a5-b5a8-718137c515db/interruptions/
```

### Response Example

```json
{}
```

### Errors

| HTTP Status | Scenario |
| ------ | ------ |
| 400 | The deployment has already finished |
| 400 | The task is still preparing and cannot be interrupted yet; retry later |
| 400 | No such deployment under the module |
| 403 | The caller is not allowed to interrupt, or the target application is not managed by the caller |
| 404 | The application or module does not exist |
