### Resource Description
Get App concise information

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Call example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/lists/minimal
```

### Return result
```json
{
    "count": 2,
    "results": [
        {
            "application": {
                "id": "674b1572-7acf-4ee5-8edb-4e241c981234",
                "code": "app11",
                "name": "app11"
            },
            "product": null
        },
        {
            "application": {
                "id": "493f0d62-9b19-4799-923b-001fb741234",
                "code": "arrluo123",
                "name": "arrluoYang"
            },
            "product": {
                "name": "arrluoYang"
            }
        }
	]
}
```