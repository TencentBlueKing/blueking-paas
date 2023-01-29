### Resource Description

Query the list of all "blue whale plug-in" type applications on the platform, which is only used by internal systems

### Authentication mode

Use Bearer method for authentication. Please apply to the administrator for specific authentication.

### Input parameter Description
| Field         | Type | Required | Description                                                  |
|-----------------------|----------|-----|------------------------------------------------------------------|
| private_token         |  string   | no | Token allocated by PaaS platform, which must be provided when the app identity of the requester is not authenticated by PaaS platform |
| search_term           |  string   | no | Filter keywords to match code and name fields                                  |
| order_by              |  string   | no | Sorting, default is "encrypted," and supports "encrypted,""code" and "encrypted code"                |
| has_deployed          |  boolean  |no   | Filter by "has plug-in been deployed" and do not filter by default                                    |
| distributor_code_name | string   | no | Filter by "authorized user code," such as "bksops," which is not filtered by default                    |
| tag                   | integer  | 否   |  Filter by plugin tag and do not filter by default                    |
| limit                 |  integer  |no   | Paging parameter, total, default is 100                                             |
| offset                |  integer  | no       | Paging parameter, deviation number, default is 0                                             |

### Return result

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
        "name": "tag-1",
        "code_name": "tag1"
      }     
    }
  ]
}
```

### Return result description

| Field | Type | Description                                   |
|--------------|----------|---------------------------------------------------|
| has_deployed | bool     | Indicates whether the plug-in has been deployed after creation, which can be filtered by`has_deployed` parameters|