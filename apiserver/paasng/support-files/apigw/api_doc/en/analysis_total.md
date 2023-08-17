### Feature Description

Query the total access volume of the application within the specified time range.

### Request Parameters

#### 1. Path Parameters:

|   Parameter Name   |    Parameter Type  |  Required  |     Parameter Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | Yes | Application ID, e.g. "monitor" |
| module   | string | Yes | Module name, e.g. "default" |
| env   | string | Yes | Environment name, e.g. "stag", "prod" |
| source_type   | string | Yes | Access value source, optional values "ingress" (access log statistics), "user_tracker" (website access statistics) |

#### 2. Interface Parameters:

|   Parameter Name   |    Parameter Type  |  Required  |     Parameter Description     |
| ------------ | ------------ | ------ | ---------------- |
| start_time   | date | Yes | Start time, e.g. "2020-05-20" |
| end_time   | date | Yes | End time, e.g. "2020-05-22" |

### Request Example

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{Enter your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/envs/{env}/analysis/m/{source_type}/metrics/total?start_time={start_time}&end_time={end_time}
```

### Response Result Example

```javascript
{
  "site": {
    "type": "app",
    "name": "--",
    "id": 38
  },
  "result": {
    "results": {
      "pv": 100,
      "uv": 12
    },
    "source_type": "tracked_pv_by_site",
    "display_name": "Total site access volume"
  }
}
```

### Response Result Parameter Description

| Field |   Type |  Description |
| ------ | ------ | ------ |
| site.type | string | Site type |
| site.name | string | Site name |
| site.id | int | Site ID |
| result.results.pv | int | Page views |
| result.results.uv | int | Unique visitors |
| result.source_type | string | Access value source |
| result.display_name | string | Display name |