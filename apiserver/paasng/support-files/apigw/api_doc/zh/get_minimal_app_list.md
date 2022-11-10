### 资源描述
获取 App 简明信息

### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 调用示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/lists/minimal
```

### 返回结果
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