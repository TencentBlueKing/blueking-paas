### Description
Query the basic information of the application to which the MySQL Enhanced Service instance database belongs based on the database name.

### Request Parameters

#### 1. Path Parameters:

|   Parameter Name   |    Parameter Type  |  Required  |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| db_name   | string | Yes | Database name |

#### 2. API Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/services/mysql/{db_name}/related_applications_info/
```

### Response Example
```
{
    "id": "d53450b6-fd5b-49b6-883f-e64030377a52",
    "code": "bk_app_codexxxx",
    "name": "Application Name",
    "administrators": [
        "admin"
    ],
    "devopses": [
        "admin2"
    ],
    "developers": [
        "admin1"
    ],
    "last_operator": "admin1"
}
```

### Response Parameters Description

| Field |   Type | Description |
| ------ | ------ | ------ |
| id | string | Application ID |
| code | string | Application code |
| name | string | Application name |
| administrators | list | Application administrators |
| devopses | list | DevOps personnel |
| developers | list | Developers |
| last_operator | string | Last operator |