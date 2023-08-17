### 功能描述

获取云原生应用在指定环境中的当前部署状态。

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string   | 是   | 应用 ID  |
| module   | string   | 是   | 模块名称，如 "default" |
| env      | string   | 是   | 环境名称，可选值 "stag" / "prod" |

#### 2、接口参数：
暂无


### 请求示例

```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "access_token": "{{填写你的 AccessToken}}"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/cnative/specs/applications/{app_code}/modules/{module}/envs/{env}/mres/status/
```
#### 获取你的 access_token

在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 返回结果示例

```json
{
  "deployment": {
    "deploy_id": 1,
    "status": "ready",
    "reason": "AppAvailable",
    "message": "",
    "last_transition_time": "2023-01-05T15:01:30+08:00",
    "operator": "user",
    "created": "2023-01-05T15:01:15.524240+08:00"
  },
  "ingress": {
    "url": "http://.../"
  },
  "conditions": [
    {
      "type": "AppAvailable",
      "status": "True",
      "reason": "AppAvailable",
      "message": ""
    },
    {
      "type": "AppProgressing",
      "status": "True",
      "reason": "NewRevision",
      "message": ""
    },
    {
      "type": "AddOnsProvisioned",
      "status": "Unknown",
      "reason": "Initial",
      "message": ""
    },
    {
      "type": "HooksFinished",
      "status": "True",
      "reason": "Finished",
      "message": ""
    }
  ],
  "events": []
}
```

### 返回结果参数说明

| 参数名称   | 参数类型      | 参数说明                         |
| ---------- | ------------- | -------------------------------- |
| deployment | object        | 最新部署状态总览                 |
| ingress    | object        | 对外暴露的可访问地址             |
| conditions | array[object] | 资源当前详细状态                 |

`deployment` 字段详细说明：

| 参数名称   | 参数类型 | 参数说明                                                     |
| ---------- | -------- | ------------------------------------------------------------ |
| status     | string   | 当前部署状态，可选值：pending / progressing / ready / error / unknown，其中 ready 表示部署正常完成 |