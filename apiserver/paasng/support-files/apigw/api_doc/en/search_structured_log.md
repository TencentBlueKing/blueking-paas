### Feature Description
Query standard output logs

### Request Parameters

#### 1. Path Parameters:

|   Parameter Name   |    Parameter Type  |  Required  |     Parameter Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | Yes | Application ID |
| module   | string | Yes | Module name, such as "default" |

#### 2. Interface Parameters:

| Parameter Name              | Parameter Type | Required | Parameter Description                                                             |
|-----------------------|----------|-----|------------------------------------------------------------------|
| log_type              | string   | Yes   | Log type, optional values: "STRUCTURED" "STANDARD_OUTPUT" "INGRESS", default value: "STRUCTURED" |
| time_range            | string   | Yes   | Time range, optional values: "5m" "1h" "3h" "6h" "12h" "1d" "3d" "7d" "customized" |
| start_time            | string   | No   | Required when time_range is "customized"                                |
| end_time              | string   | No   | Required when time_range is "customized"                |
| page              | int   | Yes   | Integer greater than 0               |
| page_size              | int   | Yes   | Integer greater than 0                |

**Note**: The log query parameters are consistent with the ES query syntax, please refer to: https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/system/applications/{app_code}/modules/{module}/log/structured/list/?time_range=1h'
```

### Response Result Example
```javascript
{
    "code": 0,
    "data": {
        "page": {
            "page": 1,
            "page_size": 20,
            "total": 1
        },
        "logs": [
            {
                "region": "default",
                "app_code": "appid",
                "environment": "stag",
                "process_id": "web",
                "stream": "django",
                "message": "xxx",
                "detail": {
                    "json.asctime": "2022-04-15 17:21:33,770",
                    "json.funcName": "info",
                    "json.levelname": "INFO",
                    "json.lineno": 43,
                    "json.message": "xxx",
                    "json.process": 34,
                    "json.thread": 139842183358536
                },
                "ts": "2022-04-15 17:21:33"
            }
        ]
    }
}
```

### Response Result Parameter Description

| Field |   Type |  Description |
| ------ | ------ | ------ |
| code | int | Return code, 0 means success |
| data | dict | Return data |
| data.page | dict | Pagination information |
| data.page.page | int | Current page number |
| data.page.page_size | int | Number of items per page |
| data.page.total | int | Total number of records |
| data.logs | list | Log list |
| data.logs.region | string | Region |
| data.logs.app_code | string | Application ID |
| data.logs.environment | string | Environment |
| data.logs.process_id | string | Process ID |
| data.logs.stream | string | Stream |
| data.logs.message | string | Message |
| data.logs.detail | dict | Detailed information |
| data.logs.ts | string | Timestamp |