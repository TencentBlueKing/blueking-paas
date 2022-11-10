### Resource Description
View all modules under the app

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Call example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "Your access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/
```

### Request parameter Description

| Name                              | Description                                                  |
| --------------------------------- | ------------------------------------------------------------ |
| code<br/>string<br/>(url)         | App Coding<br/>code - App Coding                             |
| source_origin<br/>int<br/>(query) | Source code sources, currently showing all sources. Support 1 (code repository)）、2（BlueKing LessCode）<br/>source_origin - Source code sources, currently showing all sources. Support 1 (code repository) 、`2`（BlueKing LessCode） |

### Return result
```json
[
    {
        "id": "4fd1848d-cd89-4bdf-ae90-423eeaccf874",
        "name": "default",
        "source_origin": 2,
        "is_default": true
    }
]
```

### Return result description



| Description:  | application module (compact)            |
| ------------- | --------------------------------------- |
| id            | string<br/>module UUID                  |
| name          | string<br/>module name, such as default |
| Is is_default | bool<br/>the default module             |

