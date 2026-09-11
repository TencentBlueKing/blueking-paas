### Function Description
Create an AI Agent application with application credentials. The caller must have the AIDEV system role. The administrator is the `operator` in the request, who must already be registered in the Developer Center. The application ID must start with `ai-`. This API only creates the application and does not deploy it. The response does not include the application secret.

The three creation modes match the user-facing API: fixed template package, git repository, and engineless third-party app.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. Interface Parameters:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| code | string | Yes | Application ID. Must start with ai-. Length 3-20. |
| name | string | Yes | Application name |
| operator | string | Yes | Username of a user already registered in the Developer Center. This user becomes the administrator. |
| is_engineless | boolean | No | Create as an engineless third-party app. Default false. |
| is_isolated | boolean | No | Deploy to an isolated environment. Default false. |
| source_config | object | No | Git source config. When provided, the app is created from a git repository. |
| bkapp_spec | object | No | Build config. Required when source_config is provided. |
| app_tenant_mode | string | No | Application tenant mode |
| app_tenant_id | string | No | Tenant ID. Empty string for a global app. |

### Request Example
```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -d '{"code": "ai-demo", "name": "ai-demo", "operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/ai_agent/
```

### Response Example
```
{
    "application": {
        "id": "479ca05c-962a-43d2-bd2c-af7735f2ede1",
        "name": "ai-demo",
        "modules": [
            {
                "name": "default",
                "is_default": true,
                "language": "Python"
            }
        ],
        "code": "ai-demo",
        "name_en": "ai-demo",
        "type": "cloud_native",
        "is_plugin_app": true,
        "is_ai_agent_app": true,
        "language": "Python",
        "is_active": true,
        "is_deleted": false,
        "last_deployed_date": null
    }
}
```

### Response Parameter Description

| Field | Type | Description |
|-------|------|-------------|
| id | string | Application ID |
| name | string | Application name |
| modules | list | Application modules |
| code | string | Application code |
| name_en | string | Application English name |
| type | string | Application type |
| is_plugin_app | boolean | Whether it is a plugin application |
| is_ai_agent_app | boolean | Whether it is an AI Agent tool |
| language | string | Application language |
| is_active | boolean | Whether it is active |
| is_deleted | boolean | Whether it has been deleted |
| last_deployed_date | string | Last deployment date |

#### Modules
| Field | Type | Description |
|-------|------|-------------|
| name | string | Module name |
| is_default | boolean | Whether it is the default module |
| language | string | Module language |
