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
```javascript
{
  "plugin": {
    "id": "70604e3d6491472eb0066ff6f7b75617",
    "region": "ieod",
    "name": "bkplugindemo2",
    "code": "bk-plugin-demo2",
    "logo_url": "https://example.com/app-logo/blueking_app_default.png",
    "has_deployed": true,
    "creator": "username",
    "created": "2021-08-13 10:37:29",
    "updated": "2021-08-13 10:37:29"
  },
  "deployed_statuses": {
    "stag": {
      "deployed": true,
      "addresses": [
        {
          "address": "http://stag-dot-bk-plugin-demo2.example.com",
          "type": 2
        },
        {
          "address": "http://foo.example.com",
          "type": 4
        }
      ]
    },
    "prod": {
      "deployed": false,
      "addresses": []
    }
  },
  "profile": {
    "introduction": "a demo plugin",
    "contact": "user1"
  }
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