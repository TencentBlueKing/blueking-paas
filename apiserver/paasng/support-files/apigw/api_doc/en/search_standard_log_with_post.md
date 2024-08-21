### Description

Query application standard output logs.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code       | string         | Yes      | Application ID, such as "monitor" |
| module         | string         | Yes      | Module name, such as "default" |

#### 2. API Parameters:

| Parameter Name | Type | Required | Description |
|-------------|--------| ------ |-------------|
| time_range  | string | Yes | Time range，one of "5m" "1h" "3h" "6h" "12h" "1d" "3d" "7d" "customized" |
| start_time  | string | No | Start time, input if time time_range = "customized" |
| end_time    | string | No | End time, input if time time_range = "customized" |
| scroll_id   | string | No | Scroll ID |
| page        | int    | No | Page，Integer greater than 0  |
| page_size   | int    | No | Page size，Integer greater than 0  |


### Request Example

```bash
curl -X POST -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/log/standard_output/list/?time_range=1h'
```

### Response Result Example
#### Success Response
```json
{
    "code": 0,
    "data": {
        "scroll_id": "scroll id",
        "logs": [
            {
                "environment": "prod",
                "process_id": "web",
                "pod_name": "pod name",
                "message": "message",
                "timestamp": "2024-08-20 12:21:08"
            }
        ],
        "total": 10299,
        "dsl": "dsl"
    }
}
```

#### Exception Response
example 1
```json
{
    "code": "QUERY_LOG_FAILED",
    "detail": "Query log failed: ..."
}
```
example 2
```json
{
    "code": "VALIDATION_ERROR",
    "detail": "...",
    "fields_detail": {
        "time_range": [
            "this field can't be empty。"
        ]
    }
}
```

### Response Result Parameter Description

| Field          | Type         | Description       |
| -------------- | ------------ | ----------------- |
| code           | integer      | Status code       |
| data           | object       | Returned data     |
| data.scroll_id | string       | ES scroll_id for pagination |
| data.logs      | []object     | Log list          |
| data.total     | integer      | Log count         |
| data.dsl       | string       | DSL query         |

data.logs field description
| Field          | Type         | Description       |
| -------------- | ------------ | ----------------- |
| environment    | string       | Running environment, "prod" or "stag" |
| message        | string       | Log message       |
| pod_name       | string       | Pod name          |
| process_id     | string       | Process unique type        |
| timestamp      | string       | Timestamp         |