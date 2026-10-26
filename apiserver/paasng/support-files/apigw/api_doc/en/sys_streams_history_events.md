### Function Description

Query the deployment logs of an AI Agent application using application credentials. The caller must have the AIDEV system role, and the application of the deployment must be an AI Agent application, otherwise 403 is returned.

The response is the same as the user-facing API `streams_history_events`.

### Request Parameters

#### 1. Path Parameters

| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | --------------------- |
| channel_id | string | Yes | Deployment ID |

#### 2. Interface Parameters

| Field | Type | Required | Description |
| ------- | ------ | ---------- | ------------- |
| last_event_id | int | No | Last event id. Default 0. |

### Request Example

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/streams/22d0e9c8-9cfc-45a5-b5a8-718137c515db/history_events
```

### Response Example

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
    "data": "Project deployment succeeded"
  },
  {
    "id": 138,
    "event": "close",
    "data": ""
  }
]
```

### Response Parameter Description

| Field | Type | Description |
| ----- | ------- | -------------------------------------------- |
| id | integer | Event ID |
| event | string | Event type, enum values: [init, close, msg, title] |
| data | string | Event content |
