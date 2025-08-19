### 功能描述
获取部署历史

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：
暂无。

### 请求示例

```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your access_token"}'  http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{appcode}/deployments/lists
```

### 返回结果示例
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

### 返回结果参数说明

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| count | int | 部署历史数量 |
| next | string/null | 下一页链接 |
| previous | string/null | 上一页链接 |
| results | array | 部署历史列表 |

results
| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| id | string | 部署历史ID |
| status | string | 部署状态 |
| operator | object | 操作者信息 |
| created | string | 创建时间 |
| environment | string | 环境 |
| repo | object | 仓库信息 |
| deployment_id | string | 部署ID |

operator
| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| username | string | 用户名 |
| id | string | 用户ID |

repo
| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| url | string | 仓库地址 |
| comment | string | 备注 |
| type | string | 类型 |
| name | string | 名称 |
| revision | string | 版本号 |