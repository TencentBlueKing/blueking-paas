### Resource Description

Query the access data grouped and aggregated by the user dimension in the time interval

### Input parameter Description

|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   |  string |yes| App ID (app id), you can get it from BlueKing Developer Center -> App Basic Settings -> Basic Information -> Authentication Information |
| app_secret | string |no| The security key (app secret) can be obtained from BlueKing Developer Center -> App Basic Settings -> Basic Information -> Authentication Information |

### Path parameter

|   Field   | Type   | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   |  string |yes| App ID, e.g. "Monitor" |
| module   |  string | yes      | Module name, such as "default"|
| env   |  string | yes      | Environment name, e.g. "Stag,""prod"|
| source_type   |  string |yes| Access value source, optional values "ingress"(access log statistics), "user_tracker"(web site access statistics)|

### Parameter Description

|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| start_time   |  date |yes| Start time, e.g. "2020-05-20"|
| end_time   |  date |yes| End time, e.g. "2020-05-22"|
| ordering | string | yes      | Sort options, recommended value "sort pv"|
| offset  | int |no| Paging parameter, default is 0|
| limit   |  int |no| Paging parameter, default is 30, maximum is 100|

### Call example

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{填写你的 AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/envs/{env}/analysis/m/{source_type}/metrics/dimension/user?start_time={start_time}&end_time={end_time}&ordering=-pv
```


### Return result

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