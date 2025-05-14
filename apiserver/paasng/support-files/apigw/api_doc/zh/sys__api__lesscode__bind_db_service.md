### 功能描述
尝试绑定数据库增强服务

当前 API 默认值提供给蓝鲸运维开发平台（应用ID：bk_lesscode）

### 请求参数

#### 1、路径参数：
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code       | string         | Yes      | 应用 ID, 例如 "apigw-api-test" |
| module         | string         | Yes      | 模块名, e.g. "default" |

### 请求示例
```
curl -X POST -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/appid1/modules/default/lesscode/bind_db_service
```

### 返回结果
#### 正常返回
http状态码200
body为空

#### 异常返回
http状态码非200