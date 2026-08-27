### Function Description
Create or update an environment variable by key. Creates the variable when it does not exist in the given environment; otherwise updates `value` / `description`.

Redeploy after changing variables so they are injected into processes.

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code | string | Yes | Application ID, e.g. "appid1" |
| module | string | Yes | Module name, e.g. "default" |
| config_var_key | string | Yes | Variable name, e.g. "KEY1". Must match `[A-Z][A-Z0-9_]*` |

#### 2. Body Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| environment_name | string | Yes | Effective environment: stag, prod, or _global_ |
| value | string | No | Variable value. Required when creating; omitted on update to keep the current value |
| description | string | No | Description, up to 200 characters |
| is_sensitive | boolean | No | Whether the value is sensitive. Only applied on create |

### Request Example
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{"environment_name":"stag","value":"0.0.1","description":"d0.0.1 version"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/config_vars/KEY1/
```

### Response Example

**Status Code Explanation:**
- **201**: Created or updated successfully (empty body)
- **400**: Invalid parameters, e.g. missing `value` when creating
