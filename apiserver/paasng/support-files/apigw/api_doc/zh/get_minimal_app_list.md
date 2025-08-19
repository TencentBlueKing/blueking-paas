### 功能描述
获取 App 简明信息

### 请求参数

#### 1、路径参数：
暂无

#### 2、接口参数：
暂无

### 请求示例

```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/lists/minimal
```

### 返回结果示例
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

### 返回结果参数说明

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| count | int | App 数量 |
| results | list | App 信息列表 |

results
| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| application | dict | App 信息 |
| product | dict | 产品信息 |

application
| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| id | string | App UUID |
| code | string | App ID(bk_app_code)  |
| name | string | App 名称 |

product
| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| name | string | 产品名称 |