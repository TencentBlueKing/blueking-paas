### Description
Obtain the database connection information for the specified application, module, and environment.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code       | string         | Yes      | Application ID        |
| module         | string         | Yes      | Module name           |
| env            | string         | Yes      | Environment, e.g. "prod" |

#### 2. API Parameters:
None.

### Request Example
```
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "appid1", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/applications/appid1/modules/default/envs/prod/lesscode/query_db_credentials
```

### Response Result Example
```json
{
    "credentials": {
        "MYSQL_HOST": "--",
        "MYSQL_PORT": --,
        "MYSQL_NAME": "--",
        "MYSQL_USER": "--",
        "MYSQL_PASSWORD": "--"
    }
}

# Failure response
{
    "code": "CANNOT_READ_INSTANCE_INFO",
    "detail": "Failed to read enhanced service instance information: Unable to obtain valid configuration information."
}

```

### Response Result Parameter Description

| Parameter Name   | Parameter Type | Parameter Description          |
| ---------------- | -------------- | ------------------------------ |
| credentials      | dict           | Database connection information|
| MYSQL_HOST       | string         | Database host address          |
| MYSQL_PORT       | int            | Database port                  |
| MYSQL_NAME       | string         | Database name                  |
| MYSQL_USER       | string         | Database username              |
| MYSQL_PASSWORD   | string         | Database password              |
| code             | string         | Error code                     |
| detail           | string         | Error details                  |