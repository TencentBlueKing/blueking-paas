### 功能描述
查询某个“蓝鲸插件”类型应用的详细信息，仅供内部系统使用。

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明               |
| -------- | -------- | ---- | -------------------- |
| code     | string   | 否   | 位置参数，待查询插件的 code |

#### 2、接口参数：
暂无。

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bk_plugins/bk-plugin-demo2/
```

### 返回结果示例
#### 正常返回
```javascript
{
    "plugin": {
        "id": "id",
        "region": "default",
        "name": "example",
        "code": "example",
        "logo_url": "http://bkpaas.example.com/static/images/plugin-default.svg",
        "has_deployed": true,
        "creator": "name",
        "created": "2024-07-25 14:45:26",
        "updated": "2024-07-25 14:45:26",
        "tag_info": {
            "id": 1,
            "name": "未分类",
            "code_name": "OTHER",
            "priority": 1
        }
    },
    "deployed_statuses": {
        "stag": {
            "deployed": true,
            "addresses": [
                {
                    "address": "http://apps.example.com/stag--example/",
                    "type": 2
                },
                {
                    "address": "http://apps.example.com/stag--default--example/",
                    "type": 2
                }
            ]
        },
        "prod": {
            "deployed": true,
            "addresses": [
                {
                    "address": "http://apps.example.com/example/",
                    "type": 2
                },
                {
                    "address": "http://apps.example.com/prod--example/",
                    "type": 2
                },
                {
                    "address": "http://apps.example.com/prod--default--example/",
                    "type": 2
                }
            ]
        }
    },
    "profile": {
        "introduction": "",
        "contact": "name",
        "api_gw_name": "bp-example",
        "api_gw_id": 36,
        "api_gw_last_synced_at": "2024-07-25 14:48:36",
        "tag": 1
    }
}
```

#### 异常返回
```
{
    "detail": "No Application matches the given query.",
    "code": "ERROR"
}
```

### 返回结果参数说明
- 当通过 code 无法查询到插件时，API 将返回 404 状态码

| 参数名称          | 参数类型 | 参数说明                                                  |
|-------------------|----------|-------------------------------------------------------|
| plugin            | object   | 插件基本信息                                              |
| deployed_statuses | object   | 插件在各环境上的部署情况，未部署时 `addresses` 字段为 `[]` |
| profile           | object   | 插件的档案信息                                            |

`deployed_statuses` 对象字段说明：

| 参数名称  | 参数类型      | 参数说明               |
|-----------|---------------|--------------------|
| deployed  | boolean       | 是否已经部署过         |
| addresses | array[object] | 当前环境下所有访问地址 |

`addresses` 元素对象字段说明：

| 参数名称 | 参数类型 | 参数说明                                            |
|----------|----------|-------------------------------------------------|
| address  | str      | 访问地址                                            |
| type     | integer  | 地址类型。说明： 2 - 默认地址；4 - 用户添加的独立域名。 |

`profile` 元素对象字段说明：

| 参数名称     | 参数类型 | 参数说明                     |
|--------------|----------|--------------------------|
| introduction | str      | 插件简介信息                 |
| contact      | str      | 插件联系人，多个插件用 ; 分隔 |
| api_gw_name    | string         | API 网关名称 |
| api_gw_id      | int            | API 网关ID |
| api_gw_last_synced_at| string   | API 网关最近同步时间 |
| tag            | int            | tag  |