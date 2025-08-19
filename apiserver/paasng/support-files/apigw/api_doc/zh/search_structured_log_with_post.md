### 功能描述
查询标准输出日志

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| code   | string | 是 | 应用 ID |
| module_name   | string | 是 | 模块名称，如 "default" |

#### 2、接口参数：

| 参数名称 | 类型 | 是否必填 | 描述 |
|------|------| ------ |-------------|
| time_range  | string | 是 | 时间范围, 可选值："5m" "1h" "3h" "6h" "12h" "1d" "3d" "7d" "customized"  |
| start_time  | string | 否 | 开始时间, time_range为"customized"时需要填写|
| end_time    | string | 否 | 结束时间, time_range为"customized"时需要填写 |
| scroll_id   | string | 否 | 滚动ID |
| page        | int    | 否 | 页, 大于 0 的整数 |
| page_size   | int    | 否 | 页长, 大于 0 的整数 |

**说明**：日志查询参数与 ES 的查询语法一致，可参考：https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html

### 请求示例
```bash
curl -X POST -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/system/applications/{code}/modules/{module_name}/log/structured/list/?time_range=1h'
```

### 返回结果示例
#### 正常返回
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

#### 异常返回
例1
```json
{
    "code": "QUERY_LOG_FAILED",
    "detail": "查询日志失败: ..."
}
```
例2
```json
{
    "code": "VALIDATION_ERROR",
    "detail": "...",
    "fields_detail": {
        "time_range": [
            "该字段是必填项。"
        ]
    }
}
```

### 返回结果参数说明

| 字段 |   类型 |  描述 |
| ------ | ------ | ------ |
| code | int | 返回码，0表示成功 |
| data | dict | 返回数据 |
| data.page | dict | 分页信息 |
| data.page.page | int | 当前页码 |
| data.page.page_size | int | 每页数量 |
| data.page.total | int | 总记录数 |
| data.logs | list | 日志列表 |
| data.logs.region | string | 区域 |
| data.logs.app_code | string | 应用ID |
| data.logs.environment | string | 环境 |
| data.logs.process_id | string | 进程唯一类型 |
| data.logs.stream | string | 流 |
| data.logs.message | string | 消息 |
| data.logs.detail | dict | 详细信息 |
| data.logs.ts | string | 时间戳 |