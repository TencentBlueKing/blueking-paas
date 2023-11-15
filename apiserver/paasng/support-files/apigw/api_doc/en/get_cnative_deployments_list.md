### Description

Retrieve the deployment history of cloud-native applications in a specified environment.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description                |
| -------------- | -------------- | -------- | ------------------------------------ |
| app_code       | string         | Yes      | Application ID                       |
| module         | string         | Yes      | Module name, e.g., "default"         |
| env            | string         | Yes      | Environment name, "stag" / "prod"    |

#### 2. API Parameters:

| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| offset         | int            | No       | Offset      |
| limit          | int            | No       | Page size   |



### Request Example

```
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "access_token": "{{your AccessToken}}"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/cnative/specs/applications/appid1/modules/default/envs/prod/mres/deployments/
```

#### Get your access_token

Before calling the interface, please obtain your access_token first. For specific guidance, please refer to [Using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS/DevelopTools/BaseGuide/topics/paas/access_token)

### Response Example

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

### Response Parameter Description

| Field                     | Type   | Required | Description          |
| ------------------------- | ------ | -------- | -------------------- |
| count                     | int    | Yes      | Total number of results |
| next                      | string | Yes      | Next page link       |
| previous                  | string | Yes      | Previous page link   |
| results                   | list   | Yes      | Deployment history list |
| results.id                | int    | Yes      | Deployment history ID |
| results.operator          | string | Yes      | Operator             |
| results.region            | string | Yes      | Region               |
| results.created           | string | Yes      | Creation time        |
| results.updated           | string | Yes      | Update time          |
| results.application_id    | string | Yes      | Application ID       |
| results.environment_name  | string | Yes      | Environment name     |
| results.name              | string | Yes      | Deployment history name |
| results.status            | string | Yes      | Deployment status    |
| results.reason            | string | Yes      | Deployment reason    |
| results.message           | string | Yes      | Deployment message   |
| results.last_transition_time | string | Yes   | Last status transition time |
| results.revision          | int    | Yes      | Deployment revision version |