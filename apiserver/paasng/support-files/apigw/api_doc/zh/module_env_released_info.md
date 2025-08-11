### 功能描述
查询应用模块环境部署信息

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| code   | string | 是 | 应用 ID |
| module_name   | string | 是 | 模块名称 |
| environment   | string | 是 | 环境名称 |

#### 2、接口参数：
暂无。

### 请求示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{code}/modules/{module_name}/envs/{environment}/released_info/
```

### 返回结果示例
```json
{
  "deployment": {
    "id": "--",
    "status": "--",
    "operator": {
      "id": "--",
      "username": "--",
      "provider_type": 2
    },
    "created": "--",
    "deployment_id": "--",
    "environment": "--",
    "repo": {
      "source_type": "--",
      "type": "--",
      "name": "--",
      "url": "--",
      "revision": "--",
      "comment": ""
    }
  },
  "exposed_link": {
    "url": "--"
  }
}
```

### 返回结果参数说明

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| deployment | dict | 部署信息 |
| exposed_link | dict | 暴露的链接信息 |

deployment
| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| id | string | 部署 ID |
| status | string | 部署状态 |
| operator | dict | 操作者信息 |
| created | string | 创建时间 |
| deployment_id | string | 部署 ID |
| environment | string | 环境名称 |
| repo | dict | 仓库信息 |

operator
| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| id | string | 操作者 ID |
| username | string | 操作者用户名 |
| provider_type | int | 提供者类型 |

repo
| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| source_type | string | 源类型 |
| type | string | 类型 |
| name | string | 仓库名称 |
| url | string | 仓库 URL |
| revision | string | 修订版本 |
| comment | string | 备注 |

exposed_link
| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| url | string | 链接地址 |