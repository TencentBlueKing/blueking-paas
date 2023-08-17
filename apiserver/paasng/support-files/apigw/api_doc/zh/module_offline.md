### 功能描述
App 下架接口，用于将指定的 App 从指定环境中下架。

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | 是 | 应用 ID |
| module   | string | 是 | 模块名称，如 "default" |
| env | string | 是 | 环境名称，可选值 "stag" / "prod" |

#### 2、接口参数：
暂无。

### 请求示例
```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{填写你的 AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{填写你的AppCode}}/modules/{{填写你的模块名}}/envs/{填写App部署环境:stag或prod}/offlines/
```

#### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 返回结果示例
```json
{
    "offline_operation_id": "22d0e9c8-9cfc-45a5-b5a8-718137c515db"
}
```

### 返回结果参数说明

|   参数名称   |  参数类型  |           参数说明             |
| ------------ | ---------- | ------------------------------ |
|     offline_operation_id | string  |  下架操作 ID |