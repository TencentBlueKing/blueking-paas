### Feature Description
A simple description of resource registration

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. Interface Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description                                                                                       |
| -------------- | -------------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| app_code       | string         | Yes      | Application ID (app id), can be obtained from Blueking Developer Center -> Application Basic Settings -> Basic Information -> Authentication Information |
| app_secret     | string         | No       | Security secret (app secret), can be obtained from Blueking Developer Center -> Application Basic Settings -> Basic Information -> Authentication Information |

### Request Example
```python
from bkapigw.paasv3.shortcuts import get_client_by_request
client = get_client_by_request(request)
# Fill in parameters
kwargs = {

}
result = client.api.api_test(kwargs)
```

### Response Result Example
```json
# Internal Edition
{
    "credentials": {
        "GCS_MYSQL_HOST": "--",
        "GCS_MYSQL_PORT": --,
        "GCS_MYSQL_NAME": "--",
        "GCS_MYSQL_USER": "--",
        "GCS_MYSQL_PASSWORD": "--"
    }
}

# Enterprise Edition
{
    "credentials": {
        "MYSQL_HOST": "--",
        "MYSQL_PORT": --,
        "MYSQL_NAME": "--",
        "MYSQL_USER": "--",
        "MYSQL_PASSWORD": "--"
    }
}

# Failure Return
{
    "code": "CANNOT_READ_INSTANCE_INFO",
    "detail": "Failed to read enhanced service instance information: Unable to obtain valid configuration information."
}

```

### Response Result Parameter Description

| Parameter Name    | Parameter Type | Parameter Description         |
| ----------------- | -------------- | ------------------------------ |
| credentials       | dict           | Database connection information|
| GCS_MYSQL_HOST    | string         | Database host address          |
| GCS_MYSQL_PORT    | int            | Database port                  |
| GCS_MYSQL_NAME    | string         | Database name                  |
| GCS_MYSQL_USER    | string         | Database username              |
| GCS_MYSQL_PASSWORD| string         | Database password              |
| MYSQL_HOST        | string         | Database host address (Enterprise Edition) |
| MYSQL_PORT        | int            | Database port (Enterprise Edition) |
| MYSQL_NAME        | string         | Database name (Enterprise Edition) |
| MYSQL_USER        | string         | Database username (Enterprise Edition) |
| MYSQL_PASSWORD    | string         | Database password (Enterprise Edition) |
| code              | string         | Error code                     |
| detail            | string         | Error details                  |