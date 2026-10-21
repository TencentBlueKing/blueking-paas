### Function Description

Deploy an AI Agent application to the specified environment using application credentials. The caller must have the AIDEV system role, and the target application must be an AI Agent application, otherwise 403 is returned.

The deployment logic is the same as the user-facing API `deploy_with_module`. Only the operator is specified by the `operator` field in the request body. The `operator` is only recorded as the operator; its application permissions are not checked, and the environment deployment role protection does not apply. Build debugging (`advanced_options.debug_enabled`) is not supported.

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
| version_type | string | Yes | Version type, use package when deploying via source package |
| version_name | string | Yes | Version name, the source package version when deploying via source package |
| revision | string | No | Revision, the source package version when deploying via source package |
| operator | string | Yes | Username of the operator, only used for recording. Virtual accounts are allowed. |
| advanced_options | object | No | Advanced options, same as the user-facing API, debug_enabled is not supported |

### Request Example

```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -d '{"version_type": "package", "version_name": "0.0.5", "revision": "0.0.5", "operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/envs/stag/deployments/
```

### Response Example

```json
{
    "stream_url": "/streams/22d0e9c8-9cfc-45a5-b5a8-718137c515db",
    "deployment_id": "22d0e9c8-9cfc-45a5-b5a8-718137c515db"
}
```

### Response Parameter Description

| Field | Type | Description |
| ------- | ------ | ------------- |
| stream_url | string | Deployment log output stream ID |
| deployment_id | string | Deployment operation ID |
