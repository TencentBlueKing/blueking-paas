### Resource Description

Query the log of the blue whale app

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Path interface description

|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   yes   | App ID    |
|   module |   string     |   yes   | Module name, such as "default"|

### Input parameter Description
| Field         | Type | Required | Description                                                  |
|-----------------------|----------|-----|------------------------------------------------------------------|
| log_type              |  string   | yes | Log type, optional value: "STRUCTURED" "STANDARD_OUTPUT" "Ingres," default value: "STRUCTURED"|
| time_range            |  string   | yes | Time range, optional values: "5m," "1h," "3h," "6h," "12h," "1d," "3d,""7d," "customized"|
| start_time            |  string   | no | Required when time_range is "customized"                                |
| end_time              |  string   | no | Required when time_range is "customized"                |

**note**: the log query parameters are consistent with the query syntax of ES. Please refer to: https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html


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