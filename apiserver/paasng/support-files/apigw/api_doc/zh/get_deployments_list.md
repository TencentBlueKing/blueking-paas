### 功能描述
获取部署历史

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | 是 | 应用 ID，如 "vision" |
| module   | string | 是 | 模块名称，如 "default" |

#### 2、接口参数：
暂无。

### 请求示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{appcode}/modules/{module_name}/deployments/lists/
```

### 返回结果示例
```json
{
    "count": 27,
    "next": "http://bkpaas.example.com/backend/api/bkapps/applications/vision/modules/default/deployments/lists/?limit=12&offset=12",
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
                "url": "repo url",
                "revision": "141c46a87160afa4f33d280ddc368bf2c12fb5c7",
                "comment": ""
            }
        },
    ]
}
```

### 返回结果参数说明

| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| count | integer | 是 | 部署历史总数 |
| next | string | 否 | 下一页链接 |
| previous | string | 否 | 上一页链接 |
| results | array | 是 | 部署历史列表 |

results
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| id | string | 是 | 部署历史ID |
| status | string | 是 | 部署状态（successful, failed, pending） |
| operator | object | 是 | 操作者信息 |
| created | string | 是 | 创建时间 |
| deployment_id | string | 是 | 部署ID |
| environment | string | 是 | 部署环境 |
| repo | object | 是 | 仓库信息 |

operator
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| id | string | 是 | 操作者ID |
| username | string | 是 | 操作者用户名 |
| provider_type | integer | 是 | 提供者类型 |

repo
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| source_type | string | 是 | 仓库源类型 |
| type | string | 是 | 分支类型 |
| name | string | 是 | 分支名称 |
| url | string | 是 | 仓库地址 |
| revision | string | 是 | 版本号 |
| comment | string | 是 | 备注 |