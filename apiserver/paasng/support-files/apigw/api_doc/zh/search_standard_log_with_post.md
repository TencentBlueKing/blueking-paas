### 功能描述

查询应用标准输出日志。

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string   | 是   | 应用 ID，如 "monitor" |
| module   | string   | 是   | 模块名称，如 "default" |

#### 2、接口参数：

| 参数名称     | 参数位置 | 类型                              | 是否必填 | 描述 |
| ------------ | -------- | --------------------------------- | -------- | ---- |
| end_time     | `query`  | string                            | 否       |      |
| log_type     | `query`  | string                            | 否       |      |
| scroll_id    | `query`  | string                            | 否       |      |
| start_time   | `query`  | string                            | 否       |      |
| time_range   | `query`  | string                            | 是       |      |
| data         | `body`   | SearchStandardLogWithPostBody     | 是       |      |

data
| 字段   | 类型                              | 是否必填 | 描述 |
| ------ | --------------------------------- | -------- | ---- |
| query  | SearchStandardLogWithPostParamsBodyQuery | 是       |      |
| sort   | interface{}                       | 否       | 排序，例如：{'response_time': 'desc', 'other': 'asc'} |

### 请求示例

```bash
curl -X POST -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/log/standard_output/list/?time_range=1h'
```

### 返回结果示例

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

### 返回结果参数说明

| 字段          | 类型                                            | 是否必填 | 描述       |
| ------------- | ----------------------------------------------- | -------- | ---------- |
| code          | integer                                         | 是       | 状态码     |
| data          | SearchStandardLogWithPostOKBodyData             | 是       | 返回数据   |
| data.logs     | []SearchStandardLogWithPostOKBodyDataLogsItems0 | 是       | 日志列表   |
| data.scroll_id | string                                          | 是       | ES 分页查询用的 scroll_id |
| data.total    | integer                                         | 是       | 日志数量   |