### Function Description
List user-defined environment variables of an application module (platform builtin vars are not included).

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code | string | Yes | Application ID, e.g. "appid1" |
| module | string | Yes | Module name, e.g. "default" |

#### 2. Query Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| environment_name | string | No | Filter by environment: stag / prod / _global_ |
| order_by | string | No | Sort field, default "-created", also accepts "key" |

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/config_vars/
```

### Response Example
```json
[
    {
        "id": 12,
        "key": "DEBUG",
        "value": "true",
        "environment_name": "_global_",
        "is_global": true,
        "is_sensitive": false,
        "description": "debug switch",
        "is_builtin": false
    }
]
```

### Response Fields
| Field | Type | Description |
| ----- | ---- | ----------- |
| id | int | Variable ID |
| key | string | Variable name, must match `[A-Z][A-Z0-9_]*` |
| value | string | Variable value; masked as `******` when `is_sensitive=true` |
| environment_name | string | Effective environment: stag / prod / _global_ |
| is_global | boolean | Whether the variable applies to all environments |
| is_sensitive | boolean | Whether the value is sensitive |
| description | string | Variable description |
