### Function Description
Create AI Agent Tool

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. Interface Parameters:

| Field | Type   | Required | Description          |
|-------|--------|----------|----------------------|
| code  | string | Yes      | Application ID       |
| name  | string | Yes      | Application Name     |

### Request Example
```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"access_token": "your access_token", "bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' -d '{"code": "testappcode", "name": "testappcode"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/bkapps/applications/ai_agent/
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
                "language": "Python"
            }
        ],
        "code": "testappcode",
        "name_en": "testappcode",
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

| Field                | Type     | Description                     |
|----------------------|----------|---------------------------------|
| id                   | string   | Application ID                  |
| name                 | string   | Application Name                |
| modules              | list     | Information about application modules |
| code                 | string   | Application Code                |
| name_en              | string   | Application English Name        |
| type                 | string   | Application Type                |
| is_plugin_app        | boolean  | Indicates whether it is a plugin application |
| is_ai_agent_app      | boolean  | Indicates whether it is an AI Agent tool |
| language             | string   | Application Language            |
| is_active            | boolean  | Indicates whether it is active   |
| is_deleted           | boolean  | Indicates whether it has been deleted |
| last_deployed_date   | string   | Last deployment date            |

#### Modules
| Field     | Type     | Description         |
|-----------|----------|---------------------|
| name      | string   | Module Name         |
| is_default | boolean  | Indicates whether it is the default module |
| language  | string   | Module Language      |