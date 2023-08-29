### Description
Query the detailed information of a "Blueking Plugin" type application, for internal system use only.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description          |
| -------------- | -------------- | -------- | ------------------------------ |
| code           | string         | No       | Position parameter, plugin code to be queried |

#### 2. API Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bk_plugins/bk-plugin-demo2/
```

### Response Result Example
```javascript
{
  "plugin": {
    "id": "70604e3d6491472eb0066ff6f7b75617",
    "region": "ieod",
    "name": "bkplugindemo2",
    "code": "bk-plugin-demo2",
    "logo_url": "https://example.com/app-logo/blueking_app_default.png",
    "has_deployed": true,
    "creator": "username",
    "created": "2021-08-13 10:37:29",
    "updated": "2021-08-13 10:37:29"
  },
  "deployed_statuses": {
    "stag": {
      "deployed": true,
      "addresses": [
        {
          "address": "http://stag-dot-bk-plugin-demo2.example.com",
          "type": 2
        },
        {
          "address": "http://foo.example.com",
          "type": 4
        }
      ]
    },
    "prod": {
      "deployed": false,
      "addresses": []
    }
  },
  "profile": {
    "introduction": "a demo plugin",
    "contact": "user1"
  }
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
| -------------- | -------------- | ----------------------------------- |
| introduction   | str            | Plugin introduction information     |
| contact        | str            | Plugin contact, multiple plugins separated by ; |