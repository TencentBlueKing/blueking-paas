### 功能描述
解绑应用模块与增强服务，并清理已分配的服务实例。

### 请求参数

#### 1、路径参数：

| 参数名称   | 参数类型 | 必须 | 参数说明               |
| ---------- | -------- | ---- | ---------------------- |
| app_code   | string   | 是   | 应用 ID                |
| module     | string   | 是   | 模块名称，如 "default" |
| service_id | string   | 是   | 增强服务 ID            |

#### 2、接口参数：
暂无。

### 请求示例
```
curl -X DELETE -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/services/a31e476d-5ec0-29b0-564e-5f81b5a5ef32/
```

### 返回结果示例

**状态码说明：**
- **200**：解绑成功（响应体为空）
- **404**：模块未绑定该服务
