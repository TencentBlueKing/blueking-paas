### 功能描述
查询多平台应用基本信息，可根据 id 或者 name 模糊搜索, 最多只返回前 1000 条数据，优先返回 PaaS3.0 开发者中心上的应用。

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：
| 参数名称      | 参数类型     | 是否必填 | 参数说明                           |
|---------------|--------------|---------|--------------------------------|
| keyword       | string       | 否      | 应用ID、应用名称，模糊查询 |
| limit         | int          | 否      | 默认值为 100，最大值为 100 |
| offset        | int          | 否      | 默认值为 0，最大值为 900 |

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/uni_applications/list/minimal/
```

### 返回结果示例
```javascript
{
    "count": 3,
    "next": null,
    "previous": null,
    "results": [
        {
            "code": "myapp",
            "name": "myapp"
        },
        {
            "code": "myapp2d",
            "name": "myappdfd"
        }
    ]
}
```

### 返回结果参数说明
| 参数名称      | 参数类型     | 参数说明                           |
|---------------|--------------|--------------------------------|
| count         | int          | 应用总数 |
| next          | string/null  | 下一页链接，如果没有则为 null |
| previous      | string/null  | 上一页链接，如果没有则为 null |
| results       | array        | 应用信息列表 |
| results.code  | string       | 应用ID |
| results.name  | string       | 应用名称 |