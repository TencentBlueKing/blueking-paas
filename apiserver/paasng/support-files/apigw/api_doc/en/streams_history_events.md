### Resource Description
Query deployment log

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Call example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}' http://bkapi.example.com/api/bkpaas3/prod/streams/{channel_id}/history_events
```

### Request parameter Description

| Name                                   | Description                               |
| -------------------------------------- | ----------------------------------------- |
| last_event_id <br/>integer<br/>(query) | last event id<br/>Default value : 0<br/>0 |
| channel_id  * <br/>string <br/>(path)  | 即deployment_id                           |

### Return result
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
    "data": "Trying to create CI-related resources"
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
    "data": "Successful project deployment"
  },
  {
    "id": 138,
    "event": "close",
    "data": ""
  }
]
```

### Return result description

| id*    | integer <br/>title: id<br/><br/>Event id                     |
| ------ | ------------------------------------------------------------ |
| event* | string <br/>title: event<br/><br/>event type<br/><br/>Enum:<br/>[init, close, msg, title ] |
| data*  | string <br/>title: Data <br/>minlength: 1<br/><br/>event content |

