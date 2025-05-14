### Description
Query the detailed information of a "Blueking Plugin" type application, for internal system use only.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description          |
| -------------- | -------------- | -------- | ------------------------------ |
| code           | string         | Yes       | Position parameter, plugin code to be queried |

#### 2. API Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bk_plugins/bk-plugin-demo2/
```

### Response Result Example
#### Success Response
```json
{
    "plugin": {
        "id": "id",
        "region": "default",
        "name": "example",
        "code": "example",
        "logo_url": "http://bkpaas.example.com/static/images/plugin-default.svg",
        "has_deployed": true,
        "creator": "name",
        "created": "2024-07-25 14:45:26",
        "updated": "2024-07-25 14:45:26",
        "tag_info": {
            "id": 1,
            "name": "未分类",
            "code_name": "OTHER",
            "priority": 1
        }
    },
    "deployed_statuses": {
        "stag": {
            "deployed": true,
            "addresses": [
                {
                    "address": "http://apps.example.com/stag--example/",
                    "type": 2
                },
                {
                    "address": "http://apps.example.com/stag--default--example/",
                    "type": 2
                }
            ]
        },
        "prod": {
            "deployed": true,
            "addresses": [
                {
                    "address": "http://apps.example.com/example/",
                    "type": 2
                },
                {
                    "address": "http://apps.example.com/prod--example/",
                    "type": 2
                },
                {
                    "address": "http://apps.example.com/prod--default--example/",
                    "type": 2
                }
            ]
        }
    },
    "profile": {
        "introduction": "",
        "contact": "name",
        "api_gw_name": "bp-example",
        "api_gw_id": 36,
        "api_gw_last_synced_at": "2024-07-25 14:48:36",
        "tag": 1
    }
}
```

#### Exception Response
```
{
    "detail": "No Application matches the given query.",
    "code": "ERROR"
}
```

### Response Result Parameter Description
- When the plugin cannot be queried through the code, the API will return a 404 status code.

| Parameter Name    | Parameter Type | Parameter Description                                    |
| ----------------- | -------------- | ----------------------------------------------------- |
| plugin            | object         | Basic information of the plugin                          |
| deployed_statuses | object         | Deployment status of the plugin in various environments, `addresses` field is `[]` when not deployed |
| profile           | object         | Profile information of the plugin                        |

`deployed_statuses` object field description:

| Parameter Name | Parameter Type | Parameter Description     |
| -------------- | -------------- | ------------------------- |
| deployed       | boolean        | Whether it has been deployed |
| addresses      | array[object]  | All access addresses in the current environment |

`addresses` element object field description:

| Parameter Name | Parameter Type | Parameter Description                            |
| -------------- | -------------- | ----------------------------------------------- |
| address        | str            | Access address                                  |
| type           | integer        | Address type. Description: 2 - Default address; 4 - User-added independent domain. |

`profile` element object field description:

| Parameter Name | Parameter Type | Parameter Description              |
| -------------- | -------------- | ---------------------------------- |
| introduction   | str            | Plugin introduction information    |
| contact        | str            | Plugin contact, multiple plugins separated by ; |
| api_gw_name    | string         | API gateway name |
| api_gw_id      | int             | API gateway id |
| api_gw_last_synced_at| string   | API gateway last sync time |
| tag            | int            | tag  |