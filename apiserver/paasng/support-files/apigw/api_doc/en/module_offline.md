### Description
App Unpublish Interface, used to unpublish the specified App from the specified environment.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code       | string         | Yes      | Application ID        |
| module         | string         | Yes      | Module name, e.g., "default" |
| env            | string         | Yes      | Environment name, available values: "stag" / "prod" |

#### 2. API Parameters:
None.

### Request Example
```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{Enter your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{Enter your AppCode}}/modules/{{Enter your module name}}/envs/{Enter App deployment environment:stag or prod}/offlines/
```

### Response Result Example
```json
{
    "offline_operation_id": "22d0e9c8-9cfc-45a5-b5a8-718137c515db"
}
```

### Response Result Parameter Description

| Parameter Name         | Parameter Type | Parameter Description |
| ---------------------- | -------------- | --------------------- |
| offline_operation_id   | string         | Unpublish operation ID |