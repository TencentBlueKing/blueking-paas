### 功能描述
查询平台上所有“蓝鲸插件”类型应用列表，仅供内部系统使用。

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：

| 参数名称              | 参数类型 | 是否必填 | 参数说明                                                             |
|-----------------------|----------|--------|------------------------------------------------------------------|
| search_term           | string   | 否   | 过滤关键字，会匹配 code 与 name 字段                                  |
| order_by              | string   | 否   | 排序，默认为 "-created"，支持 "created"、 "code"、"-code"                |
| has_deployed          | boolean  | 否   | 按“插件是否部署过”过滤，默认不过滤                                    |
| distributor_code_name | string   | 否   | 按“已授权使用方代号”过滤，比如 "bksops"，默认不过滤                    |
| tag                   | integer  | 否   |  按插件分类过滤，默认不过滤                    |
| limit                 | integer  | 否   | 分页参数，总数，默认为 100                                             |
| offset                | integer  | 否   | 分页参数，偏差数，默认为 0                                             |

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "bk_apigw_test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bk_plugins/
```

### 返回结果示例

```javascript
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "9eafc30c50874c34a9499cb56ccb4bfc",
      "name": "testplugin",
      "code": "testplugin",
      "logo_url": "https://example.com/app-logo/blueking_app_default.png",
      "has_deployed": false,
      "creator": "username",
      "created": "2021-08-17 19:35:25",
      "updated": "2021-08-17 19:35:25",
      "tag_info": {
          "id": 1,
          "name": "分类1",
          "code_name": "tag1"
      }
    }
  ]
}
```

### 返回结果参数说明

| 参数名称       | 参数类型 | 参数说明                                                      |
|----------------|----------|-----------------------------------------------------------|
| count          | int      | 返回结果的总数，表示符合条件的记录总数。                               |
| next           | string   | 下一页的链接，如果没有更多结果，则为 `null`。                          |
| previous       | string   | 上一页的链接，如果当前是第一页，则为 `null`。                          |
| results        | array    | 包含符合条件的资源项数组，每个元素为一个对象，具体结构见下文。              |
| results.id     | string   | 唯一标识符，通过该 ID 可识别该插件。                                   |
| results.name   | string   | 插件的名称。                                                |
| results.code   | string   | 插件的代码标识。                                            |
| results.logo_url| string  | 插件的 logo 图片链接，用于展示该插件的标识。                          |
| results.has_deployed | bool | 表示插件创建后是否已部署过，值为 `true` 表示已部署，`false` 表示未部署。     |
| results.creator | string  | 创建该插件的用户名。                                        |
| results.created | string  | 插件创建时间，格式为 `YYYY-MM-DD HH:mm:ss`。                   |
| results.updated | string  | 插件最后更新时间，格式为 `YYYY-MM-DD HH:mm:ss`。                 |
| results.tag_info | object  | 插件分类信息对象，包含以下字段：                                |
| results.tag_info.id | int | 插件分类的唯一标识符。                                          |
| results.tag_info.name | string | 插件分类的名称。                                           |
| results.tag_info.code_name | string | 插件分类标识。                                    |