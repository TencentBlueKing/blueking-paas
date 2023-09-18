### 功能描述
查询平台上所有“蓝鲸插件”类型应用列表（带部署信息），仅供内部系统使用。

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：

| 参数名称              | 参数类型 | 必须 | 参数说明                                                             |
|-----------------------|----------|-----|------------------------------------------------------------------|
| search_term           | string   | 否   | 过滤关键字，会匹配 code 与 name 字段                                  |
| order_by              | string   | 否   | 排序，默认为 "-created"，支持 "created"、 "code"、"-code"、"name"、"-name" |
| has_deployed          | boolean  | 否   | 按“插件是否部署过”过滤，默认不过滤                                    |
| distributor_code_name | string   | 否   | 按“已授权使用方代号”过滤，比如 "bksops"，默认不过滤                    |
| tag                   | integer  | 否   |  按插件分类过滤，默认不过滤                    |
| limit                 | integer  | 否   | 分页参数，总数，默认为 100                                             |
| offset                | integer  | 否   | 分页参数，偏差数，默认为 0                                             |

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bk_plugins/batch/detailed/
```

### 返回结果示例
```javascript
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
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
        "tag_info": {
          "id": 1,
          "name": "分类1",
          "code_name": "tag1"
        }
      },
      "deployed_statuses": {
        "stag": {
          "deployed": true,
          ]
        },
        "prod": {
          "deployed": false,
        }
      }
    }
  ]
}
```

### 返回结果参数说明

- 注意：本接口历史版本会返回 `deployed_statuses.{env}.addresses` 字段，现已移除，
  如需获取访问地址，请使用 `retrieve_bk_plugin` API

| 参数名称 | 参数类型      | 参数说明                           |
|----------|---------------|--------------------------------|
| results  | array[object] | 请参考 retrieve_bk_plugin 接口返回 |