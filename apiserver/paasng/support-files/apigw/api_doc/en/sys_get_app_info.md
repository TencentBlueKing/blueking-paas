### Description

Get the information, deploy mode and exposed urls of an AI Agent application with system API credentials. The caller must have the AIDEV system role and the target application must be an AI Agent application, otherwise a 403 is returned.

#### Tenant

System APIs do not depend on the user login state, the tenant is passed by the `X-Bk-Tenant-Id` header:

- A global application (`app_tenant_mode` is `global`) is available to all tenants;
- A single-tenant application is only available to the tenant in its `app_tenant_id`, other tenants get a 403 `APP_TENANT_MISMATCH`;
- The header is ignored when multi-tenant mode is not enabled.

### Request Parameters

#### Path parameters

| Name | Type | Required | Description |
| -------- | -------- | --- | -------- |
| app_code | string | Yes | Application ID, must be an AI Agent application |

### Request Example

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -H 'X-Bk-Tenant-Id: default' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/
```

### Response Example

```json
{
    "application": {
        "id": "c4b6f5c1d3a2410d8f9c2b7e5a6d1f30",
        "code": "ai-demo",
        "name": "AI Agent Demo",
        "type": "cloud_native",
        "is_ai_agent_app": true,
        "is_plugin_app": true,
        "deploy_policy": "default",
        "app_tenant_mode": "single",
        "app_tenant_id": "default",
        "deploy_info": {
            "stag": {
                "deployed": true,
                "url": "http://ai-demo-stag.example.com"
            },
            "prod": {
                "deployed": false,
                "url": ""
            }
        },
        "preferred_prod_url": null,
        "modules": []
    },
    "web_config": {
        "engine_enabled": true,
        "can_create_extra_modules": false
    },
    "migration_status": {
        "status": "no_need_migration",
        "error_msg": ""
    }
}
```

### Response Parameters

| Name | Type | Description |
| ------ | ------ | ------ |
| application | object | Application info, same as the `application` of the user-facing `get_app_info` API, with extra `deploy_info` / `preferred_prod_url` |
| application.deploy_policy | string | Deploy mode, `default` or `isolated` |
| application.deploy_info | object | Deploy status and exposed url of each environment, keyed by environment name |
| application.preferred_prod_url | string | Preferred production url, null when no custom domain is configured |
| web_config | object | Application level feature switches |
| migration_status | object | Cloud-native migration status |
