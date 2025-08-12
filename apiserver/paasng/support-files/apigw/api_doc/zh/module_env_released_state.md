### 功能描述
查询应用模块环境部署信息

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| code     | string   | 是   | 应用代码 |
| module_name | string | 是 | 模块名称 |
| environment | string | 是 | 环境名称 |

#### 2、接口参数：
暂无。

### 请求示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{code}/modules/{module_name}/envs/{environment}/released_state/
```

### 返回结果示例

#### 正常返回
```json
{
    "is_offlined": false,
    "deployment": {
        "id": "114392d8-9e77-4011-83a9-41f1737e2466",
        "status": "successful",
        "operator": {
            "id": "0335cce79c92",
            "username": "admin",
            "provider_type": 3,
            "avatar": ""
        },
        "created": "2024-08-16 10:07:33",
        "start_time": "2024-08-16 10:07:33",
        "complete_time": "2024-08-16 10:08:07",
        "finished_status": "release",
        "build_int_requested_at": null,
        "release_int_requested_at": null,
        "has_requested_int": false,
        "bkapp_revision_id": 247,
        "deployment_id": "114392d8-9e77-4011-83a9-41f1737e2466",
        "environment": "prod",
        "repo": {
            "source_type": null,
            "type": "tag",
            "name": "1.5.5",
            "url": "docker.example.com/bkpaas/docker/example/default:1.5.5",
            "revision": "1.5.5",
            "comment": ""
        }
    },
    "offline": null,
    "exposed_link": {
        "url": "http://apps.example.com/"
    },
    "default_access_entrance": {
        "url": "http://apps.example.com/"
    }
}
```

#### 异常返回
```json
{
    "code": "APP_NOT_RELEASED",
    "detail": "应用尚未在该环境发布过"
}
```

### 返回结果参数说明

| 字段   | 类型  | 描述         |
| ----- | ---- |  ----------- |
| is_offlined | boolean | 是否已下架 |
| deployment | object | 部署记录 |
| offline | object | 下架记录 |
| exposed_link | object | 访问地址 |
| default_access_entrance | object | 默认访问地址 |

