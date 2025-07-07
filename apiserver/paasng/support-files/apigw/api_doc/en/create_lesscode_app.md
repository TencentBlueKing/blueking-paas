### Function Description
Create a BlueKing Operations Development Platform Application

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. API Parameters:

| Field | Type | Required | Description |
| ------ | ------ | ------ | ------ |
| code | string | Yes | Application code |
| name | string | Yes | Application name |
| type | string | Yes | Application type, default is "default" |
| engine_enabled | boolean | Yes | Whether the engine is enabled |
| engine_params | dict | Yes | Engine parameters |

`engine_params`:

| Field | Type | Required | Description |
| ------ | ------ | ------ | ------ |
| source_origin | int | Yes | Source code origin |
| source_init_template | string | Yes | Initialization template, e.g., "nodejs_bk_magic_vue_spa" |

### Request Example
```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"access_token": "your_access_token", "bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' -d '{"code": "testappcode", "name": "testappcode", "type": "default", "engine_enabled": true, "engine_params": {"source_origin": 2, "source_init_template": "nodejs_bk_magic_vue_spa"}}' --insecure https://bkapi.example.com/api/bkpaas3/stag/bkapps/applications/lesscode/
```

### Response Example
```
{
    "application": {
        "id": "479ca05c-962a-43d2-bd2c-af7735f2ede1",
        "name": "testappcode",
        "modules": [
            {
                "name": "default",
                "is_default": true,
                "language": "NodeJS"
            }
        ],
        "code": "testappcode",
        "name_en": "testappcode",
        "type": "default",
        "language": "NodeJS",
        "is_active": true,
        "is_deleted": false,
        "last_deployed_date": null
    }
}
```

### Response Parameters Description

| Field | Type | Description |
| ------ | ------ | ------ |
| id | string | Application ID |
| name | string | Application name |
| modules | list | Application module information |
| code | string | Application code |
| name_en | string | Application English name |
| type | string | Application type |
| language | string | Application language |
| is_active | boolean | Whether the application is active |
| is_deleted | boolean | Whether the application is deleted |
| last_deployed_date | string | Last deployment date |

`modules`:

| Field | Type | Description |
| ------ | ------ | ------ |
| name | string | Module name |
| is_default | boolean | Whether it's the default module |
| language | string | Module language |