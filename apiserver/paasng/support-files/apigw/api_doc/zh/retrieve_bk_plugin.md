### 资源描述

查询某个“蓝鲸插件”类型应用的详细信息，仅供内部系统使用

### 认证方式

使用 Bearer 方式认证，具体的 token 请向管理员申请。

### 输入参数说明

| 参数名称      | 参数类型 | 必须 | 参数说明                   |
|---------------|----------|-----|------------------------|
| private_token | string   | 否   | PaaS 平台分配的 token,当请求方的应用身份未被 PaaS 平台认证时必须提供|
| code          | string   | 否   | 位置参数，待查询插件的 code |

### 返回结果

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

### 返回结果说明

- 当通过 code 无法查询到插件时，API 将返回 404 状态码

| 参数名称          | 参数类型 | 参数说明                                                  |
|-------------------|----------|-------------------------------------------------------|
| plugin            | object   | 插件基本信息                                              |
| deployed_statuses | object   | 插件在各环境上的部署情况，未部署时 `addresses` 字段为 `[]` |

`deployed_statuses` 对象字段说明：

| 参数名称  | 参数类型      | 参数说明               |
|-----------|---------------|--------------------|
| deployed  | boolean       | 是否已经部署过         |
| addresses | array[object] | 当前环境下所有访问地址 |
| profile   | object        | 插件的档案信息         |


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