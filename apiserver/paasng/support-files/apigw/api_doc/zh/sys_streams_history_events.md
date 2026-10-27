### 功能描述

以应用身份查询部署日志。调用方须具备 AIDEV 或 AppSpark 系统角色，且只能查询自己管理的应用的部署，否则返回 403：

- AIDEV：部署所属应用必须是 AI Agent 应用
- AppSpark：部署所属应用默认模块的源码来源必须仍为 AppSpark，且只能查询默认模块在生产环境的部署（其他模块返回 403，预发布环境返回 400）

返回结果与用户态接口 `streams_history_events` 一致。

### 请求参数

#### 1、路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | --- | -------- |
| channel_id | string | 是 | 部署 ID |

#### 2、接口参数

| 字段 | 类型 | 是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| last_event_id | int | 否 | 最后一个事件 id，默认 0 |

### 请求示例

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/streams/22d0e9c8-9cfc-45a5-b5a8-718137c515db/history_events
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
    "id": 10,
    "event": "msg",
    "data": "{\"line\": \"Preparing to build bkapp-v200115-new-app-stag ...\", \"stream\": \"STDOUT\"}"
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

| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| id | integer | 事件 id |
| event | string | 事件类型，枚举值：[init, close, msg, title] |
| data | string | 事件内容 |
