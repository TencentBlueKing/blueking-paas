### Resource Description

Query the app list (with deployment information) of all "blue whale plug-in" types on the platform, which is only used by internal systems

### Authentication mode

Use Bearer method for authentication. Please apply to the administrator for specific authentication.

### Input parameter Description

| Field         | Type | Required | Description                                                  |
|-----------------------|----------|-----|------------------------------------------------------------------|
| private_token         |  string   | no | Token allocated by PaaS platform, which must be provided when the app identity of requester is not authenticated by PaaS platform |
| search_term           |  string   | no | Filter keywords to match code and name fields                                  |
| order_by              |  string   | no | Sorting, default is "created," and supports "created,""code,""created code,""name,""created name"|
| has_deployed          |  boolean  |no   | Filter by "plug-in deployed" and do not filter by default                                    |
| distributor_code_name | string   | no | Filter by "authorized user code," such as "bksops," which is not filtered by default                    |
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

### Return result description

- Note: the historical version of this interface will return "deployed_statuses. {env} .addresses .addresses field, now removed,
  To obtain an access address, use the`retrieve_bk_plugin` api

| Field | Type  | Description                |
|----------|---------------|--------------------------------|
| results  |array [object] |Please refer to the retrieve_bk_plugin interface return|
