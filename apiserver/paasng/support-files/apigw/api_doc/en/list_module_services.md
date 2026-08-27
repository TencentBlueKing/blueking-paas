### Function Description
List addon services of an application module. The response contains three groups: bound, shared and unbound.

Call this API before binding: look up the service English name (e.g. `mysql` / `redis`) in `unbound` to get its `uuid`, then call `bind_service`.

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code | string | Yes | Application ID, e.g. "appid1" |
| module | string | Yes | Module name, e.g. "default" |

#### 2. API Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/services/
```

### Response Example
```json
{
    "bound": [
        {
            "service": {
                "uuid": "73f77c3a-dbc8-44cf-a6c5-3b1d656c4206",
                "name": "mysql",
                "display_name": "MySQL",
                "description": "MySQL database"
            },
            "provision_infos": {"stag": true, "prod": false},
            "plans": {
                "stag": {"name": "default", "description": "default plan"},
                "prod": {"name": "default", "description": "default plan"}
            },
            "ref_modules": []
        }
    ],
    "shared": [],
    "unbound": [
        {
            "uuid": "1f80d0b7-97ac-462f-9059-839666c971bc",
            "name": "redis",
            "display_name": "Redis",
            "description": "Redis cache"
        }
    ]
}
```

### Response Fields
| Field | Type | Description |
| ----- | ---- | ----------- |
| bound | list | Addon services already enabled on this module |
| bound[].service.uuid | string | Addon service UUID |
| bound[].service.name | string | Service English name |
| bound[].provision_infos | object | Whether instances are provisioned in stag / prod |
| shared | list | Services shared from another module |
| unbound | list | Visible but not yet bound services; use `uuid` here to bind |
