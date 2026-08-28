### Function Description
Get environment variables by key. The same key may exist in stag / prod / _global_, so the response is a list.

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code | string | Yes | Application ID, e.g. "appid1" |
| module | string | Yes | Module name, e.g. "default" |
| config_var_key | string | Yes | Variable name, e.g. "FOO". Must match `[A-Z][A-Z0-9_]*` |

#### 2. API Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/config_vars/FOO/
```

### Response Example
```json
[
    {
        "id": 12,
        "key": "FOO",
        "value": "bar",
        "environment_name": "stag",
        "is_global": false,
        "is_sensitive": false,
        "description": "foo var"
    }
]
```

### Response Fields
| Field | Type | Description |
| ----- | ---- | ----------- |
| id | int | Variable ID |
| key | string | Variable name |
| value | string | Variable value; sensitive values are masked |
| environment_name | string | Effective environment: stag / prod / _global_ |
| is_global | boolean | Whether the variable applies to all environments |
| is_sensitive | boolean | Whether the value is sensitive |
| description | string | Variable description |
