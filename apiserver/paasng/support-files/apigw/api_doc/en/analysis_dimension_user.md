### Feature Description
Query the aggregated access data of the application grouped by user dimension within the specified time range.

### Request Parameters

#### 1. Path Parameters:

|   Parameter Name   |    Parameter Type  |  Required  |     Parameter Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | Yes | Application ID, such as "monitor" |
| module   | string | Yes | Module name, such as "default" |
| env   | string | Yes | Environment name, such as "stag", "prod" |
| source_type   | string | Yes | Access value source, optional values "ingress" (access log statistics), "user_tracker" (website access statistics) |

#### 2. Interface Parameters:

|   Parameter Name   |    Parameter Type  |  Required  |     Parameter Description     |
| ------------ | ------------ | ------ | ---------------- |
| start_time   | date | Yes | Start time, such as "2020-05-20" |
| end_time   | date | Yes | End time, such as "2020-05-22" |
| ordering | string | Yes | Sorting option, recommended value "-pv" |
| offset  | int | No | Pagination parameter, default is 0 |
| limit   | int | No | Pagination parameter, default is 30, maximum 100 |

### Request Example
```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{Fill in your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/envs/{env}/analysis/m/{source_type}/metrics/dimension/user?start_time={start_time}&end_time={end_time}&ordering=-pv
```

### Response Result Example
```javascirpt
{
  "meta": {
    "schemas": {
      "resource_type": {
        "name": "user",
        "display_name": "Username"
      },
      "values_type": [
        {
          "name": "dept",
          "display_name": "Department",
          "sortable": false
        },
        {
          "name": "pv",
          "display_name": "Number of visits",
          "sortable": true
        }
      ]
    },
    "pagination": {
      "total": 5
    }
  },
  "resources": [
    {
      "name": "xxx",
      "values": {
        "dept": "-- / -- / --",
        "pv": 38
      },
      "display_options": null
    },
    {
      "name": "yyy",
      "values": {
        "dept": "-- / -- / --",
        "pv": 19
      },
      "display_options": null
    },
    {
      "name": "zzz",
      "values": {
        "dept": "-- / -- / --",
        "pv": 11
      },
      "display_options": null
    }
  ]
}
```

### Response Result Parameter Description

| Field |   Type |  Description |
| ------ | ------ | ------ |
| meta | object | Metadata information |
| meta.schemas | object | Field type information |
| meta.schemas.resource_type | object | Resource type information |
| meta.schemas.resource_type.name | string | Resource type name |
| meta.schemas.resource_type.display_name | string | Resource type display name |
| meta.schemas.values_type | array | Value type information |
| meta.schemas.values_type[].name | string | Value type name |
| meta.schemas.values_type[].display_name | string | Value type display name |
| meta.schemas.values_type[].sortable | bool | Whether it can be sorted |
| meta.pagination | object | Pagination information |
| meta.pagination.total | int | Total number of records |
| resources | array | Resource list |
| resources[].name | string | Username |
| resources[].values | object | User-related information |
| resources[].values.dept | string | Department information |
| resources[].values.pv | int | Number of visits |
| resources[].display_options | object | Display options (none for now) |