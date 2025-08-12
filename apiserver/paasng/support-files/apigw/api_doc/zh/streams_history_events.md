### 功能描述
查询部署日志

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| channel_id | string | 是 | 部署ID |

#### 2、接口参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| last_event_id | int | 否 | 最后一个事件id |

### 请求示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your access_token"}' http://bkapi.example.com/api/bkpaas3/prod/streams/{channel_id}/history_events
```

### 返回结果示例
```json
[
  {
    "id": 1,
    "event": "init",
    "data": ""
  },
  {
    "id": 2,
    "event": "title",
    "data": "正在尝试创建 CI 相关资源"
  },
  ...
  {
    "id": 10,
    "event": "msg",
    "data": "{\"line\": \"Preparing to build bkapp-v200115-new-app-stag ...\", \"stream\": \"STDOUT\"}"
  },
  ...
  {
    "id": 136,
    "event": "msg",
    "data": "{\"line\": \"> web instance \\\"5f265pz\\\" is ready [\\u2705]\", \"stream\": \"StreamType.STDOUT\"}"
  },
  {
    "id": 137,
    "event": "title",
    "data": "项目部署成功"
  },
  {
    "id": 138,
    "event": "close",
    "data": ""
  }
]
```

### 返回结果参数说明

| 字段 | 类型 | 是否必填 | 描述 |
| ---- | ---- | -------- | ---- |
| id | integer | 是 | 事件id |
| event | string | 是 | 事件类型，枚举值：[init, close, msg, title] |
| data | string | 是 | 事件内容 |