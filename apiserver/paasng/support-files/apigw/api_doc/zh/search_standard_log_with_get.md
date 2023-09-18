### 功能描述

查询应用标准输出日志。

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | 是 | 应用 ID，如 "monitor" |
| module   | string | 是 | 模块名称，如 "default" |

#### 2、接口参数：

| 参数名称 | 类型 | 是否必填 | 描述 |
|------|------| :------: |-------------|
| end_time | string | 否 | 结束时间 |
| log_type | string | 否 | 日志类型 |
| scroll_id | string | 否 | 滚动ID |
| start_time | string | 否 | 开始时间 |
| time_range | string | 是 | 时间范围 |

### 请求示例

```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/log/standard_output/list/?time_range=1h'
```

### 返回结果示例

```json
{
  "result": true,
  "data": {
    "scroll_id": "12345",
    "logs": [
      {
        "timestamp": "2021-08-30T10:00:00Z",
        "log_type": "stdout",
        "message": "Application started"
      },
      {
        "timestamp": "2021-08-30T10:01:00Z",
        "log_type": "stdout",
        "message": "Request received"
      }
    ]
  }
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| result | bool | 请求结果，成功为true，失败为false |
| data | dict | 返回的数据 |

data
| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| scroll_id | string | 滚动ID |
| logs | list | 日志列表 |

logs
| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| timestamp | string | 日志时间戳 |
| log_type | string | 日志类型 |
| message | string | 日志消息 |