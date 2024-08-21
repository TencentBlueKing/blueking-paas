### 功能描述
获取轻应用信息。

说明：轻应用相关 API 默认只允许标准运维（应用ID：bk_sops）调用，如需调用请联系平台管理员添加权限。

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：
| 参数名称 | 参数类型 | 是否必填 | 参数说明          |
| -------- | -------- | -------- | ----------------- |
| light_app_code | string   | 是       | 轻应用的 APP Code |

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/light-applications?light_app_code=demo_code
```

### 返回结果示例
```json
{
  "bk_error_msg": "",
  "bk_error_code": 0,
  "data": {
        "light_app_code": "ceshichajian_ycs",
        "app_name": "testapp",
        "app_url": "http://example.com",
        "introduction": "-",
        "creator": "admin",
        "logo": "",
        "developers": [
            "admin"
        ],
        "state": 4
  },
  "result": true
}
```

### 返回结果参数说明
| 名称         | 类型   | 说明              |
| ------------ | ------ | ----------------- |
| light_app_code | string | 轻应用的 APP Code |
| app_name     | string | 轻应用的名称      |
| app_url      | string | 应用链接          |
| introduction | string | 应用介绍          |
| creator      | string | 创建者            |
| logo         | string | 图标地址          |
| developers   | array  | 开发者列表        |
| state        | int    | 应用状态          |