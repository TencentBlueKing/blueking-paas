### 资源描述

查询云原生应用部署状态

### 获取你的 access_token

在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 路径参数说明

| 参数名称      | 参数类型   | 必须  | 参数说明                      |
|-----------|--------|-----|---------------------------|
| app_code  | string | 是   | 应用 ID                     |
| module    | string | 是   | 模块名称，如 default            |
| env       | string | 是   | 环境名称，可选值 stag / prod   |

### 调用示例

```bash
curl -X GET http://bkapi.example.com/api/bkpaas3/prod/cnative/specs/applications/{app_code}/modules/{module}/envs/{env}/mres/status/ \
-H 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}' \
-H 'Content-Type: application/json'
```

### 返回结果

```json
{
    "deployment": {
        "deploy_id": 2023,
        "status": "ready",
        "reason": "AppAvailable",
        "message": "",
        "last_transition_time": "2023-01-01T10:00:00+08:00",
        "operator": "admin",
        "created": "2023-01-01T10:00:00+08:00"
    },
    "ingress": {
        "url": "http://stag-dot-testcode.saas.bkexample.com/"
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
        "status": "True",
        "reason": "Provisioned",
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

| 参数名称              | 参数类型         | 参数说明           |
|-------------------|--------------|----------------|
| deployment        | object       | 部署状态信息         |
| deployment.status | string       | 部署总状态          |
| ingress           | object       | 访问入口信息         |
| conditions        | list[object] | k8s conditions |
| events            | list[object] | k8s events     |
