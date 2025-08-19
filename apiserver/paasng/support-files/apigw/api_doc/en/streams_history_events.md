### Description
Query deployment logs

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| channel_id     | string         | Yes      | Deployment ID         |

#### 2. API Parameters:
| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| last_event_id     | int         | No      | Last event id         |

### Request Example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}' http://bkapi.example.com/api/bkpaas3/prod/streams/{channel_id}/history_events
```

### Response Result Example
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
    "data": "Attempting to create CI-related resources"
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
    "data": "Project deployment succeeded"
  },
  {
    "id": 138,
    "event": "close",
    "data": ""
  }
]
```

### Response Result Parameter Description

| Field | Type    | Required | Description                                  |
| ----- | ------- | -------- | -------------------------------------------- |
| id    | integer | Yes      | Event ID                                     |
| event | string  | Yes      | Event type, enum values: [init, close, msg, title] |
| data  | string  | Yes      | Event content                                |