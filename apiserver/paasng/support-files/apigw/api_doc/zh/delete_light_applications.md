### 功能描述

删除轻应用。

说明：轻应用相关 API 默认只允许标准运维（应用ID：bk_sops）调用，如需调用请联系平台管理员添加权限。

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：

| 参数名称 | 参数类型 | 是否必填 | 参数说明          |
| -------- | -------- | -------- | ----------------- |
| light_app_code | string   | 是       | 轻应用的 APP Code |

### 请求示例
```
curl -X DELETE -H 'X-Bkapi-Authorization: {"bk_app_code": "appid", "bk_app_secret": "***"}' --insecure 'http://bkapi.example.com/api/bkpaas3/prod/system/light-applications?light_app_code=bk_sops_xxxxx'
```

### 返回结果示例

```json
{
  "bk_error_msg": "",
  "bk_error_code": 0,
  "data": {
    "count": 1
  },
  "result": true
}
```

### 返回结果参数说明

| 字段         | 类型   | 描述              |
| ------------ | ------ | ----------------- |
| count        | int    | 删除的应用数      |