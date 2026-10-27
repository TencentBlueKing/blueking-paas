### Description

Start, stop or scale a process of an AI Agent application with system API credentials. The caller must have the AIDEV system role and the target application must be an AI Agent application, otherwise a 403 is returned.

#### Tenant

The system API does not rely on user login state; the tenant is passed via the `X-Bk-Tenant-Id` header:

- Global apps (`app_tenant_mode` is `global`) are available to all tenants;
- Single-tenant apps are only available under the tenant matching their `app_tenant_id`, other tenants receive 403 `APP_TENANT_MISMATCH`;
- The header is ignored when multi-tenant mode is disabled.

### Request Parameters

#### 1. Path parameters

| Name | Type | Required | Description |
| -------- | -------- | --- | -------- |
| app_code | string | Yes | Application ID, must be an AI Agent application |
| module | string | Yes | Module name, e.g. "default" |
| env | string | Yes | Environment name, "stag" or "prod" |

#### 2. Body parameters

| Name | Type | Required | Description |
| ------ | ------ | ------ | ------ |
| operate_type | string | Yes | Operation type: start / stop / scale |
| process_type | string | Yes | Process name, e.g. web |
| target_replicas | integer | No | Target replicas, required when `operate_type` is `scale` and autoscaling is disabled |
| autoscaling | boolean | No | Whether to enable autoscaling, default false |
| scaling_config | object | No | Autoscaling config, required when autoscaling is enabled |
| operator | string | Yes | Operator username, only used for the audit record, virtual accounts are allowed |

### Request Example

```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -H 'X-Bk-Tenant-Id: default' -d '{"operate_type": "scale", "process_type": "web", "target_replicas": 2, "operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/envs/stag/processes/
```

### Response Example

```json
{
    "target_replicas": 2,
    "target_status": "start"
}
```

### Response Parameters

| Name | Type | Description |
| ------ | ------ | ------ |
| target_replicas | integer | Target replicas after the operation |
| target_status | string | Target status after the operation, start or stop |
