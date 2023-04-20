### 资源描述

获取云原生应用在指定环境中的部署历史。

### 获取你的 access_token

在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 路径接口说明

| 参数名称     | 参数类型     | 必须  | 参数说明                      |
|----------|----------|-----|---------------------------|
| app_code | string   | 是   | 应用 ID                     |
| module   | string   | 是   | 模块名称，如 "default"          |
| env      | string   | 是   | 环境名称，可选值 "stag" / "prod"  |

### 输入参数说明

| 参数名称   | 参数类型   | 必须  | 参数说明 |
|--------|--------|-----|------|
| offset | int    | 否   | 偏移量  |
| limit  | int    | 否   | 每页数量 |


### 返回结果
```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 533,
            "operator": "admin",
            "region": "",
            "created": "2023-01-10 10:00:00",
            "updated": "2023-01-10 10:00:00",
            "application_id": "516227f6-9d24-b977-4aeb-77bfe8fc2176",
            "environment_name": "stag",
            "name": "cnative-230110-655-1681116566",
            "status": "ready",
            "reason": "AppAvailable",
            "message": "",
            "last_transition_time": "2023-01-10 10:00:00",
            "revision": 655
        }
    ]
}
```
