### Function Description
Query the list of all "Blueking Plugin" type applications on the platform, for internal system use only.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. API Parameters:

| Parameter Name         | Parameter Type | Required | Parameter Description                                              |
|------------------------|----------------|----------|--------------------------------------------------------------------|
| search_term            | string         | No       | Filter keyword, will match code and name fields                    |
| order_by               | string         | No       | Sorting, default is "-created", supports "created", "code", "-code" |
| has_deployed           | boolean        | No       | Filter by "whether the plugin has been deployed", default is not filtered |
| distributor_code_name  | string         | No       | Filter by "authorized user code", such as "bksops", default is not filtered |
| tag                    | integer        | No       | Filter by plugin category, default is not filtered                 |
| limit                  | integer        | No       | Pagination parameter, total number, default is 100                 |
| offset                 | integer        | No       | Pagination parameter, offset, default is 0                         |

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "bk_apigw_test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bk_plugins/
```

### Response Result Example

```javascript
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "9eafc30c50874c34a9499cb56ccb4bfc",
      "region": "ieod",
      "name": "testplugin",
      "code": "testplugin",
      "logo_url": "https://example.com/app-logo/blueking_app_default.png",
      "has_deployed": false,
      "creator": "username",
      "created": "2021-08-17 19:35:25",
      "updated": "2021-08-17 19:35:25",
      "tag_info": {
          "id": 1,
          "name": "Category 1",
          "code_name": "tag1"
      }
    }
  ]
}
```

### Response Result Parameter Description

| Parameter Name           | Parameter Type | Description                                                      |
|--------------------------|----------------|------------------------------------------------------------------|
| count                    | int            | Total number of results that meet the criteria.                  |
| next                     | string         | Link to the next page; will be `null` if there are no more results. |
| previous                 | string         | Link to the previous page; will be `null` if currently on the first page. |
| results                  | array          | An array of resource items that meet the criteria, each element being an object with the structure defined below. |
| results.id               | string         | Unique identifier for the plugin that can be used to identify it. |
| results.name             | string         | The name of the plugin.                                         |
| results.code             | string         | The code identifier for the plugin.                             |
| results.logo_url         | string         | Link to the plugin’s logo image, used for displaying its identity. |
| results.has_deployed     | bool           | Indicates whether the plugin has been deployed after creation; `true` means deployed, `false` means not deployed. |
| results.creator          | string         | Username of the person who created the plugin.                  |
| results.created          | string         | The creation time of the plugin in the format `YYYY-MM-DD HH:mm:ss`. |
| results.updated          | string         | The last update time of the plugin in the format `YYYY-MM-DD HH:mm:ss`. |
| results.tag_info         | object         | Object containing information about the plugin's tags, including the following fields: |
| results.tag_info.id      | int            | Unique identifier for the tag.                                  |
| results.tag_info.name    | string         | Name of the tag.                                               |
| results.tag_info.code_name| string        | Code identifier for the tag.                                   |