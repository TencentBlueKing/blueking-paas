### 资源描述
App 部署接口

### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 输入参数说明
|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
|   url   |   string     |   是   |  部署源码路径(包含trunk)    |
|   revision |   string     |   是   |  源码仓库版本号 |
|   version_name | string |  是 | branch 或 tag 的名称 |
|   version_type | string |  是 |  对于 svn，支持传 trunk / tag； 对于 git，支持传 branch |

### 使用注意事项
在调用 paasv3 资源操作类方法(POST\PUT\DELETE\PATCH) 时，需要额外传递 csrf_token 保证 csrf 校验通过。你需要在 Request Headers 添加相应的 token，以下内容可以直接复制：
```json
{
	"X-CSRFToken": "HVF3oYpBhnQEjSS3703v3NMq3B6iFgNxkLY29eg1K3l2KzhzjT9GZ6IIPAvsas4K",
	"Cookie": "paasng_csrftoken=HVF3oYpBhnQEjSS3703v3NMq3B6iFgNxkLY29eg1K3l2KzhzjT9GZ6IIPAvsas4K;"
}
```

### 调用示例

#### gitlab
```bash
curl --cookie "paasng_csrftoken=HVF3oYpBhnQEjSS3703v3NMq3B6iFgNxkLY29eg1K3l2KzhzjT9GZ6IIPAvsas4K;" -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "RLjqb3t0VQ5v2ZuT0rXhz7413rKSr3"}' -H 'X-CSRFToken: HVF3oYpBhnQEjSS3703v3NMq3B6iFgNxkLY29eg1K3l2KzhzjT9GZ6IIPAvsas4K' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{填写你的AppCode}/envs/{填写App部署环境:stag或prod}/deployments/ -d '{"url": "http://gitlab.example.com/你的项目路径.git", "revision": "commit的sha值", "version_type": "branch", "version_name": "master"}' -H 'Content-Type: application/json'
```

### 返回结果
```json
{
    "stream_url": "/streams/22d0e9c8-9cfc-45a5-b5a8-718137c515db",
	"deployment_id": "22d0e9c8-9cfc-45a5-b5a8-718137c515db"
}
```

### 返回结果说明
|   参数名称   |  参数类型  |           参数说明             |
| ------------ | ---------- | ------------------------------ |
|  stream_url  |     string  |     部署日志输出流 ID          |
|     deployment_id | string  |  部署操作 ID |