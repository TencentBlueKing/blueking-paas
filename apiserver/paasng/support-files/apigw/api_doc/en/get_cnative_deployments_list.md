### Resource Description

Get the deployment history of "cloud-native" application in a given environment.

### Get your access_token

Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Path parameters

| Name     | Type   | Required | Description                                   |
| -------- | ------ | -------- | --------------------------------------------- |
| app_code | string | Y        | application code(ID)                          |
| module   | string | Y        | name of module, e.g. "default"                |
| env      | string | Y        | name of environment, choices: "stag" / "prod" |

### Query parameters

| Name   | Type   | Required | Description |
|--------|--------|----------|-------------|
| offset | int    | N        | offset      |
| limit  | int    | N        | limit       |


### Return result

```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 533,
            "operator": "admin",
            "region": "",
            "created": "2023-01-10 10:00:00",
            "updated": "2023-01-10 10:00:00",
            "application_id": "516227f6-9d24-b977-4aeb-77bfe8fc2176",
            "environment_name": "stag",
            "name": "cnative-230110-655-1681116566",
            "status": "ready",
            "reason": "AppAvailable",
            "message": "",
            "last_transition_time": "2023-01-10 10:00:00",
            "revision": 655
        }
    ]
}
```
