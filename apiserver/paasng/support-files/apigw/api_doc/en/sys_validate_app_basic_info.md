### Function Description
Validate with application credentials whether an application ID and name can be used to create an application. This API only validates and creates nothing. The caller's system role must be allowed to validate application IDs and names (such as AppSpark or AIDEV); otherwise it gets 403.

The application ID is checked against the basic Developer Center rules and must be globally unique; extra requirements of individual creation APIs (such as the ai- prefix of AI Agent apps) are not included. The application name is unique within the tenant, both the Chinese and English names are compared, and it must not collide with any global app. Unsupported characters in the name are filtered out, the same as on creation.

When the application ID or name cannot be used, the API still returns 200 and explains why in `is_valid` and `fields_detail`. It returns 400 only when the tenant parameters are invalid.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. Interface Parameters:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Application name |
| code | string | No | Application ID. Only the name is validated if omitted |
| app_tenant_mode | string | No | Application tenant mode |
| app_tenant_id | string | No | Tenant ID. Empty string for a global app. |

### Request Example
```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bk-app-spark", "bk_app_secret": "***"}' -d '{"code": "demo-app", "name": "demo-app"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/applications/validations/
```

### Response Example
```
{
    "is_valid": false,
    "fields_detail": {
        "name": [
            {
                "message": "Application with name(name_zh_cn) demo-app already exists",
                "code": "unique"
            }
        ]
    }
}
```

### Response Parameter Description

| Field | Type | Description |
|-------|------|-------------|
| is_valid | boolean | Whether both the application ID and name can be used to create an application |
| fields_detail | dict | Fields that cannot be used and why, keyed by field name (code, name) with a list of errors; empty when all can be used |

Errors in fields_detail
| Field | Type | Description |
|-------|------|-------------|
| code | string | Error code. unique means taken by another application; others mean the format is invalid (such as invalid or max_length) |
| message | string | Error message |
