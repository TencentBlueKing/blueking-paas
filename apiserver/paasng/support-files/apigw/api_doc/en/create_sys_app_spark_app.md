### Function Description
Create an AppSpark application with application credentials. The caller must have the AppSpark system role; other roles get 403.

The application is a standard cloud-native application: it is neither a plugin app nor an AI Agent app, and it shows up in the user's application list in the Developer Center. Both the staging and production environments are created on the default cluster, and access control stays disabled. The default module's source origin is AppSpark, it is deployed via source packages, and its language is Python.

This API only creates the application and does not deploy it. The response does not include the application secret. The source package and build method are provided later through the source package upload API.

The administrator is the `operator` in the request, who must be a real user already registered in the Developer Center. Virtual accounts are not allowed. The administrator is only set on creation; afterwards users manage members in the Developer Center themselves.

Once a user switches the default module to code repository deployment in the Developer Center, the application is no longer managed by AppSpark, and further calls from AppSpark to the related APIs return 403.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. Interface Parameters:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| code | string | Yes | Application ID, validated by the standard Developer Center rules: lowercase letters, digits and hyphens, length 3-20, globally unique |
| name | string | Yes | Application name |
| operator | string | Yes | Username of the administrator, who must be registered in the Developer Center |
| app_tenant_mode | string | No | Application tenant mode |
| app_tenant_id | string | No | Tenant ID. Empty string for a global app. |

### Request Example
```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "app-spark", "bk_app_secret": "***"}' -d '{"code": "demo-app", "name": "demo-app", "operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/app_spark/
```

### Response Example
```
{
    "application": {
        "id": "479ca05c-962a-43d2-bd2c-af7735f2ede1",
        "name": "demo-app",
        "modules": [
            {
                "name": "default",
                "is_default": true,
                "language": "Python"
            }
        ],
        "code": "demo-app",
        "name_en": "demo-app",
        "type": "cloud_native",
        "is_plugin_app": false,
        "is_ai_agent_app": false,
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
| id | string | Application UUID |
| name | string | Application name |
| modules | list | Module information |
| code | string | Application code |
| name_en | string | English name |
| type | string | Application type |
| is_plugin_app | boolean | Whether it is a plugin app |
| is_ai_agent_app | boolean | Whether it is an AI Agent tool |
| language | string | Programming language |
| is_active | boolean | Whether active |
| is_deleted | boolean | Whether deleted |
| last_deployed_date | string | Last deployment time |


modules
| Field | Type | Description |
|-------|------|-------------|
| name | string | Module name |
| is_default | boolean | Whether it is the default module |
| language | string | Module language |
