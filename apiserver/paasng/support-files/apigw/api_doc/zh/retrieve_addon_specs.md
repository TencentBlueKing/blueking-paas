### 功能描述
获取增强服务的规格组合

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string   | 是   | 应用 ID，如 "apigw-api-test" |
| module   | string   | 是   | 模块名称，如 "default" |
| service_id | string | 是 | 服务ID，如 "946ee404-df67-4013-a92f-9cc116ff50dc" |

#### 2、接口参数：
暂无。

### 请求示例
```
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/applications/appid1/modules/default/services/946ee404-df67-4013-a92f-9cc116ff50dc/specs/
```

### 返回结果示例
```
{
    "results": {
        "version": "5.7",
        "app_zone": "universal"
    }
}
```

### 返回结果参数说明

| 字段        | 类型   | 是否必填 | 描述             |
| ----------- | ------ | -------- | ---------------- |
| results     | dict   | 是       | 返回数据         |
| results.version | string | 是   | 版本信息         |
| results.app_zone | string | 是   | 应用区域         |