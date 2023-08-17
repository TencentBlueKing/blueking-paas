### Feature Description
Query the list of all "Blueking Plugin" type applications on the platform (with deployment information), for internal system use only.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. Interface Parameters:

| Parameter Name        | Parameter Type | Required | Parameter Description                                                |
|-----------------------|----------------|----------|----------------------------------------------------------------------|
| search_term           | string         | No       | Filter keyword, will match code and name fields                      |
| order_by              | string         | No       | Sorting, default is "-created", supports "created", "code", "-code", "name", "-name" |
| has_deployed          | boolean        | No       | Filter by "whether the plugin has been deployed", default is not filtered |
| distributor_code_name | string         | No       | Filter by "authorized user code", such as "bksops", default is not filtered |
| tag                   | integer        | No       | Filter by plugin category, default is not filtered                   |
| limit                 | integer        | No       | Pagination parameter, total number, default is 100                   |
| offset                | integer        | No       | Pagination parameter, offset, default is 0                           |

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bk_plugins/batch/detailed/
```

### Response Result Example
```javascript
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
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
        "tag_info": {
          "id": 1,
          "name": "Category1",
          "code_name": "tag1"
        }
      },
      "deployed_statuses": {
        "stag": {
          "deployed": true,
          ]
        },
        "prod": {
          "deployed": false,
        }
      }
    }
  ]
}
```

### Response Result Parameter Description

- Note: The historical version of this interface will return the `deployed_statuses.{env}.addresses` field, which has been removed.
  To get the access address, please use the `retrieve_bk_plugin` API.

| Parameter Name | Parameter Type | Parameter Description                 |
|----------------|----------------|---------------------------------------|
| results        | array[object]  | Please refer to the retrieve_bk_plugin API return |