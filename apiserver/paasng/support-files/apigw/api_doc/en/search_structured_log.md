### Resource Description

查询标准输出日志

### Authentication mode

Use Bearer method for authentication. Please apply to the administrator for specific authentication.

### Path parameter

|   Field   |    Type  |  Required  |     Description     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   yes   |  App ID, e.g. "Monitor"   |
|   module |   string     |   yes   |   Module name, such as "default" |

### Input parameter Description
| Field              | Type | Required | Description      |
|-----------------------|----------|-----|------------------------------------------------------------------|
| private_token | string      | no   | Token allocated by PaaS platform, which must be provided when the app identity of the requester is not authenticated by PaaS platform|
| log_type              | string   | yes   | Log type, optional values: "STRUCTURED" "STANDARD_OUTPUT" "INGRESS", default value: "STRUCTURED" |
| time_range            | string   | yes   | Time range, optional values: "5m" "1h" "3h" "6h" "12h" "1d" "3d" "7d" "customized" |
| start_time            | string   | no   | Required when time_range is "customized"                                |
| end_time              | string   | no  | Required when time_range is "customized"               |
| page              | int   | yes   | >=1              |
| page_size              | int   | yes   | >=1               |

**Tips**: The log query parameters are consistent with the ES query syntax, please refer to:https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html


### Return result

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