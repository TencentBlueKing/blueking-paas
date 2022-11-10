### Resource Description

Query the total number of visits to the app in the time interval.

### Input parameter Description

|   Field   | Type | Required | Description                                                  |
| ------------ | ------------ | ------ | ---------------- |
| app_code   |  string |yes| App ID (app id), you can get it from BlueKing Developer Center -> App Basic Settings -> Basic Information -> Authentication Information |
| app_secret | string |no| The security key (app secret) can be obtained from BlueKing Developer Center -> App Basic Settings -> Basic Information -> Authentication Information |

### Path parameter

|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   |  string |yes| App ID, e.g. "Monitor" |
| module   |  string | yes      | Module name, such as "default"|
| env   |  string | yes      | Environment name, e.g. "Stag,""prod"|
| source_type   |  string | yes      | Access value source, optional values "ingress"(access log statistics), "user_tracker"(web site access statistics)|

### Parameter Description

|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| start_time   |  date |yes| Start time, e.g. "2020-05-20"|
| end_time   |  date |yes| End time, e.g. "2020-05-22"|

### Call example

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{填写你的 AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/envs/{env}/analysis/m/{source_type}/metrics/total?start_time={start_time}&end_time={end_time}
```


### Return result

```javascirpt
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
    "display_name": "Total site visits"
  }
}
```