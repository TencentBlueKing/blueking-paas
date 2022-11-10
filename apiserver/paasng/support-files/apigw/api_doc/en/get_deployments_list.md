### Resource Description
Get deployment history

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Call example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{你的appcode}/modules/{你的模块名}/deployments/lists/
```

### Return result
```json
{
    "count": 27,
    "next": "http://staging.bkpaas.example.com/backend/api/bkapps/applications/vision/modules/default/deployments/lists/?limit=12&offset=12",
    "previous": null,
    "results": [
        {
            "id": "36ef5721-7313-48fa-a59a-1dc47c585828",
            "status": "failed",
            "operator": {
                "id": "0227c0eb979e5289b5",
                "username": "admin",
                "provider_type": 2
            },
            "created": "2020-08-24 14:49:10",
            "deployment_id": "36ef5721-7313-48fa-a59a-1dc47c585828",
            "environment": "prod",
            "repo": {
                "source_type": "bk_gitlab",
                "type": "branch",
                "name": "master",
                "url": "http://git.example.com/v3-awesome-app.git",
                "revision": "141c46a87160afa4f33d280ddc368bf2c12fb5c7",
                "comment": ""
            }
        },
    ]
}
```

### Return result description

| count*   | integer                                     |
| -------- | ------------------------------------------- |
| next     | string($uri)<br/>x-nullable: true           |
| previous | string($uri)<br/>x-nullable: true           |
| results* | dict, see the table below for field details |

#### results Field Details

| id       | string($uuid)<br/>title: UUID<br/>readOnly: true             |
| -------- | ------------------------------------------------------------ |
| status   | string<br/>title: 部署状态Enum:<br/>[ successful, failed, pending ] |
| operator | string<br/>title: Operator<br/>readOnly: true                |
| created  | string($date-time)<br/>title: Created<br/>readOnly: true     |

