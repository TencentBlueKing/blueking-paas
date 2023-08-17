### Feature Description
View all modules under the application


### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code       | string         | Yes      | Application code      |

#### 2. Interface Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/
```

#### Get your access_token
Before calling the interface, please obtain your access_token first. For specific guidance, please refer to [Using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Response Result Example
```json
[
    {
        "id": "4fd1848d-cd89-4bdf-ae90-423eeaccf874",
        "name": "default",
        "source_origin": 2,
        "is_default": true
    }
]
```

### Response Result Parameter Description

| Field         | Type   | Description       |
| ------------- | ------ | ----------------- |
| id            | string | Module UUID       |
| name          | string | Module name       |
| source_origin | int    | Source code origin|
| is_default    | bool   | Whether it is the default module |