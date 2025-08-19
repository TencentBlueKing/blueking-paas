### 功能描述
App 部署接口，用于部署应用到指定环境。

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
|   url   |   string     |   是   |  部署源码路径(包含trunk)    |
|   revision |   string     |   是   |  源码仓库版本号 |
|   version_name | string |  是 | branch 或 tag 的名称 |
|   version_type | string |  是 |  对于 svn，支持传 trunk / tag； 对于 git，支持传 branch |


### 请求示例

#### gitlab
```bash
curl --cookie "paasng_csrftoken=HVF3oYpBhnQEjSS3703v3NMq3B6iFgNxkLY29eg1K3l2KzhzjT9GZ6IIPAvsas4K;" -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "RLjqb3t0VQ5v2ZuT0rXhz7413rKSr3"}' -H 'X-CSRFToken: HVF3oYpBhnQEjSS3703v3NMq3B6iFgNxkLY29eg1K3l2KzhzjT9GZ6IIPAvsas4K' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{AppCode}/envs/{env:stag/prod}/deployments/ -d '{"url": "http://gitlab.example.com/xxx.git", "revision": "commit sha", "version_type": "branch", "version_name": "master"}' -H 'Content-Type: application/json'
```

### 返回结果示例
```json
{
    "stream_url": "/streams/22d0e9c8-9cfc-45a5-b5a8-718137c515db",
	"deployment_id": "22d0e9c8-9cfc-45a5-b5a8-718137c515db"
}
```

### 返回结果参数说明
|   参数名称   |  参数类型  |           参数说明             |
| ------------ | ---------- | ------------------------------ |
|  stream_url  |     string  |     部署日志输出流 ID          |
|     deployment_id | string  |  部署操作 ID |