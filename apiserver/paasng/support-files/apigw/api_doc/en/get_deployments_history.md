### Resource Description
Get deployment history

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Call example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}'  http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{你的appcode}/deployments/lists
```

### Return result
```json
{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": "e09fbf57-303f-483c-85b5-d41d03ec1234",
            "status": "successful",
            "operator": {
                "username": "kunliangwu",
                "id": "xxxxxxxxxxxx"
            },
            "created": "2018-07-27 14:55:53",
            "environment": "stag",
            "repo": {
                "url": "http://svn.o.tencent.com/apps/ktest1/trunk",
                "comment": "",
                "type": "trunk",
                "name": "trunk",
                "revision": "26933"
            },
            "deployment_id": "e09fbf57-303f-483c-85b5-d41d03ec1234"
        },
        {
            "id": "5d5d964d-825d-4fcb-ae42-ab143e6d1234",
            "status": "successful",
            "operator": {
                "username": "admin",
                "id": "xxxxxxxxxxx"
            },
            "created": "2018-07-10 21:47:31",
            "environment": "stag",
            "repo": {
                "url": "http://svn.o.tencent.com/apps/ktest1/trunk",
                "comment": "",
                "type": "trunk",
                "name": "trunk",
                "revision": "26933"
            },
            "deployment_id": "5d5d964d-825d-4fcb-ae42-ab143e6d1234"
        }
	]
}
```