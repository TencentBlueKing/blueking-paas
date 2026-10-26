### Description

Get the add-on service instances bound to an AI Agent application module with system API credentials, including the observability entrance in `admin_url`. The caller must have the AIDEV system role and the target application must be an AI Agent application, otherwise a 403 is returned.

The response structure is the same as the user-facing `get_service_instance_by_module` API. A 404 is returned when the module is not bound with the service.

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
| service_id | string | Yes | Add-on service ID |

#### 2. Query parameters

None.

### Request Example

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -H 'X-Bk-Tenant-Id: default' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/services/a31e476d-5ec0-29b0-564e-5f81b5a5ef32/
```

### Response Example

```json
{
    "count": 1,
    "results": [
        {
            "service_instance": {
                "config": {
                    "bk_app_code": "ai-demo",
                    "env": "stag",
                    "admin_url": "https://bkm.example.com/?space_uid=bksaas__ai-demo#/apm/application"
                },
                "credentials": "{}",
                "sensitive_fields": [],
                "hidden_fields": {}
            },
            "environment": "stag",
            "environment_name": "Staging",
            "usage": "{}"
        }
    ],
    "plans": {
        "stag": {
            "name": "default-otel",
            "description": "otel service"
        }
    }
}
```

### Response Parameters

| Name | Type | Description |
| ------ | ------ | ------ |
| count | int | Number of results |
| results | list | Detailed service instance list |
| results[].service_instance.config | object | Service instance config, **the observability entrance is the `admin_url` field** |
| results[].service_instance.credentials | string | Service credentials (JSON string, sensitive fields removed) |
| results[].service_instance.sensitive_fields | list | Sensitive fields |
| results[].service_instance.hidden_fields | object | Hidden fields |
| results[].environment | string | Environment name, e.g. "stag" |
| results[].environment_name | string | Environment display name |
| results[].usage | string | Usage information |
| plans | object | Add-on plan of each environment, keyed by environment name |
