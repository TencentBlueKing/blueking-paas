### 资源描述
App 部署接口

### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 路径接口说明

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   是   |  应用 ID    |
|   module |   string     |   是   |  模块名称，如 "default" |
|   env | string |  是 | 环境名称，可选值 "stag" / "prod" |

### 输入参数说明
|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
|   url   |   string     |   是   |  部署源码路径(包含trunk)    |
|   revision |   string     |   是   |  源码仓库版本号 |
|   version_name | string |  是 | branch 或 tag 的名称 |
|   version_type | string |  是 |  对于 svn，支持传 trunk / tag； 对于 git，支持传 branch |

### 调用示例

#### gitlab

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "RLjqb3t0VQ5v2ZuT0rXhz7413rKSr3"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{填写你的AppCode}/modules/default/envs/{填写App部署环境:stag或prod}/deployments/ -d '{"url": "http://git.example.com/你的项目路径.git", "revision": "commit的sha值", "version_type": "branch", "version_name": "master"}' -H 'Content-Type: application/json'
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