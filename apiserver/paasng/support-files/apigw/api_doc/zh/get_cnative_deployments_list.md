### 功能描述

获取云原生应用在指定环境中的部署历史。

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明                      |
| -------- | -------- | ---- | --------------------------- |
| app_code | string   | 是   | 应用 ID                     |
| module   | string   | 是   | 模块名称，如 "default"          |
| env      | string   | 是   | 环境名称，可选值 "stag" / "prod"  |

#### 2、接口参数：

| 参数名称 | 参数类型 | 是否必填 | 描述     |
| -------- | -------- | -------- | -------- |
| offset   | int      | 否       | 偏移量   |
| limit    | int      | 否       | 每页数量 |


### 请求示例

```
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "access_token": "{{your AccessToken}}"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/cnative/specs/applications/appid1/modules/default/envs/prod/mres/deployments/
```

#### 获取你的 access_token

在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS/DevelopTools/BaseGuide/topics/paas/access_token)

### 返回结果示例

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

### 返回结果参数说明

| 字段               | 类型   | 是否必填 | 描述             |
| ------------------ | ------ | -------- | ---------------- |
| count              | int    | 是       | 结果总数         |
| next               | string | 是       | 下一页链接       |
| previous           | string | 是       | 上一页链接       |
| results            | list   | 是       | 部署历史列表     |
| results.id         | int    | 是       | 部署历史ID       |
| results.operator   | string | 是       | 操作人           |
| results.region     | string | 是       | 区域             |
| results.created    | string | 是       | 创建时间         |
| results.updated    | string | 是       | 更新时间         |
| results.application_id | string | 是   | 应用ID           |
| results.environment_name | string | 是 | 环境名称         |
| results.name       | string | 是       | 部署历史名称     |
| results.status     | string | 是       | 部署状态         |
| results.reason     | string | 是       | 部署原因         |
| results.message    | string | 是       | 部署信息         |
| results.last_transition_time | string | 是 | 最后状态切换时间 |
| results.revision   | int    | 是       | 部署修订版本号   |