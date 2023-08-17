### 功能描述
获取 App 详细信息


### 请求参数

#### 1、接口参数：

| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| limit | number | 否 | 结果数量 |
| offset | number | 否 | 翻页跳过数量 |
| exclude_collaborated | boolean | 否 | 是否排除拥有协作者权限的应用，默认不排除。如果为 true，意为只返回我创建的 |
| include_inactive | boolean | 否 | 是否包含已下架应用，默认不包含 |
| language | string | 否 | APP 编程语言 |
| search_term | string | 否 | 搜索关键字 |
| source_origin | int | 否 | 源码来源，目前支持 1（代码仓库）、2（蓝鲸 LessCode） |
| type | str | 否 | 按应用类型筛选，目前支持：default（默认）、engineless_app（无引擎应用）、bk_plugin（蓝鲸插件） |
| order_by | string | 否 | 排序，可选值：code、created、last_deployed_date、latest_operated_at， 默认为升序，前面加 - 后为降序，如 -created |

### 请求示例
```bash
curl -X GET -H 'Accept: */*' -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}' http://bkapi.example.com/api/bkpaas3/bkapps/applications/lists/detailed
```

#### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 返回结果示例
```json
{
    "count": 2,
    "next": "http://bkpaas.example.com/backend/api/bkapps/applications/lists/detailed?limit=12&amp;offset=12",
    "previous": null,
    "results": [
        {
            "application": {
                "id": "130bd72a-dbf5-419c-8357-9ed914341234",
                "region_name": "内部版",
                "logo_url": "http://example.com/app-logo/blueking_app_default.png",
                "deploy_status": true,
                "deploy_info": {
                    "stag": {
                        "url": "http://apps.example.com/ieod-bkapp-aaaa-stag/",
                        "deployed": true
                    },
                    "prod": {
                        "url": "http://apps.example.com/ieod-bkapp-aaaa-prod/",
                        "deployed": true
                    }
                },
                "region": "ieod",
                "created": "2018-04-25 12:08:54",
                "updated": "2018-06-19 16:54:37",
                "owner": "0236c4ff908f528b",
                "code": "verylongnameaaaa",
                "name": "我就是v3t",
                "language": "Go",
                "source_init_template": "go_gin_hello_world",
                "source_type": "bk_svn",
                "source_repo_id": 432,
                "app_type": "backend",
                "is_active": true,
                "last_deployed_date": null,
                "creator": "0236c4ff908f528b",
                "is_deleted": false
            },
            "product": null,
            "marked": true
        },
        {
            "application": {
                "id": "d403880b-6c46-4edf-b1a0-24363b61234",
                "region_name": "混合云版",
                "logo_url": "http://example.com/app-logo/blueking_app_default.png",
                "deploy_status": true,
                "deploy_info": {
                    "stag": {
                        "url": "http://apps.example.com/clouds-bkapp-appid-stag/",
                        "deployed": true
                    },
                    "prod": {
                        "url": null,
                        "deployed": false
                    }
                },
                "region": "clouds",
                "created": "2018-04-10 16:34:36",
                "updated": "2018-04-10 16:34:36",
                "owner": "0236c4ff908f528b",
                "code": "appid8",
                "name": "测试8",
                "language": "Python",
                "source_init_template": "dj18_hello_world",
                "source_type": "bk_svn",
                "source_repo_id": 425,
                "app_type": "backend",
                "is_active": true,
                "last_deployed_date": null,
                "creator": "0236c4ff908f528b",
                "is_deleted": false
            },
            "product": null,
            "marked": false
        }
	]
}

```

### 返回结果参数说明

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| count | number | 总数 |
| next | string | 下一页地址 |
| previous | string | 上一页地址 |
| results | array | 结果列表，包含应用信息 |

results 内部字段说明：

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| application | object | 蓝鲸应用信息 |
| product | object | 应用市场应用信息 |
| marked | boolean | 是否关注 |

application 内部字段说明：

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| id | string | 应用 UUID |
| region | string | 应用区域 |
| region_name | string | region 对应的中文名称 |
| source_type | string | 应用源码托管类型 |
| source_repo_id | string | 应用源码托管 id |
| is_active | boolean | 应用是否活跃 |
| last_deployed_date | boolean | 应用最近部署时间 |
| code | string | 应用 Code |
| name | string | 应用名称 |
| logo_url | string | 应用 Logo 地址 |
| language | string | 应用使用的编程语言 |
| source_init_template | string | 应用初始化时使用的模板名称 |
| created | string | 应用创建时间 |
| updated | string | 应用修改时间 |
| deploy_info | object | 部署信息 |

deploy_info 内部字段说明：

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| stag | object | 阶段信息 |
| prod | object | 生产信息 |

stag 和 prod 内部字段说明：

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| deployed | bool | 是否部署 |
| url | string | 访问链接 |

product 内部字段说明：

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| name | string | 应用 UUID |
| logo | string | 应用的 logo 地址 |