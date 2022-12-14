### 资源描述

获取云原生应用在指定环境中的当前部署状态。

### 获取你的 access_token

在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 路径接口说明

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   是   |  应用 ID    |
|   module |   string     |   是   |  模块名称，如 "default" |
|   env | string |  是 | 环境名称，可选值 "stag" / "prod" |

### 输入参数说明

暂无

### 返回结果

本接口将返回应用在指定环境中的当前部署状态，示例响应如下所示：

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

### 返回结果说明

|   参数名称   |  参数类型  |           参数说明             |
| ------------ | ---------- | ------------------------------ |
| deployment | object | 最新部署状态总览  |
| ingress | object | 对外暴露的可访问地址 |
| conditions | array[object] | 资源当前详细状态，每类 condition 分别代表对应阶段的详细状态说明 |

`deployment` 字段详细说明：

|   参数名称   |  参数类型  |           参数说明             |
| ------------ | ---------- | ------------------------------ |
| status | string | 当前部署状态，可选值：pending / progressing / ready / error / unknown，其中 ready 表示部署正常完成 |
