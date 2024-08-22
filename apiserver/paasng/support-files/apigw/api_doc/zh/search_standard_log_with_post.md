### 功能描述

查询应用标准输出日志。

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string   | 是   | 应用 ID，如 "monitor" |
| module   | string   | 是   | 模块名称，如 "default" |

#### 2、接口参数：

| 参数名称 | 类型 | 是否必填 | 描述 |
|------|------| ------ |-------------|
| time_range  | string | 是 | 时间范围, 可选值："5m" "1h" "3h" "6h" "12h" "1d" "3d" "7d" "customized"  |
| start_time  | string | 否 | 开始时间, time_range为"customized"时需要填写|
| end_time    | string | 否 | 结束时间, time_range为"customized"时需要填写 |
| scroll_id   | string | 否 | 滚动ID |
| page        | int    | 否 | 页, 大于 0 的整数 |
| page_size   | int    | 否 | 页长, 大于 0 的整数 |

### 请求示例

```bash
curl -X POST -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/log/standard_output/list/?time_range=1h'
```

### 返回结果示例
#### 正常返回
```json
{
  "code": 200,
  "data": {
    "logs": [
      {
        "environment": "prod",
        "message": "log message",
        "pod_name": "app-1",
        "process_id": "123",
        "timestamp": "2021-01-01T00:00:00Z"
      }
    ],
    "scroll_id": "scroll_id",
    "total": 1
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

| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| code           | integer      | 状态码     |
| data           | object       | 数据       |
| data.scroll_id | string       | ES 滚动ID  |
| data.logs      | []object     | Log 列表   |
| data.total     | integer      | Log 数量   |
| data.dsl       | string       | DSL查询语句 |

data.logs[] 内部字段描述
| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| environment    | string       | 运行, "prod" 或 "stag" |
| message        | string       | Log 消息      |
| pod_name       | string       | Pod 名        |
| process_id     | string       | 进程唯一类型        |
| timestamp      | string       | 时间戳        |