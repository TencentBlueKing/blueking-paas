### 功能描述

以应用身份中断一次进行中的部署。调用方须具备 AIDEV 或 AppSpark 系统角色，且只能操作自己管理的应用，否则返回 403：

- AIDEV：目标应用必须是 AI Agent 应用
- AppSpark：目标应用默认模块的源码来源必须仍为 AppSpark，且只能中断默认模块在生产环境的部署（其他模块返回 403，预发布环境的部署返回 400）

中断逻辑与用户态接口一致，区别是不要求 `operator` 是部署发起人。`operator` 只记入应用的操作记录，不校验其应用权限。

接口成功只代表中断请求已被受理。中断通常需要 1-5 秒生效，调用方应继续轮询 `sys_get_deployment_result`，以最终的 `interrupted` 状态为准。

### 请求参数

#### 1、路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | --- | -------- |
| app_code | string | 是 | 应用 ID，必须是调用方管理的应用 |
| module | string | 是 | 模块名称，如 "default" |
| deployment_id | string | 是 | 部署任务 ID |

#### 2、接口参数

| 字段 | 类型 | 是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| operator | string | 是 | 中断操作人用户名，只记入操作记录，允许使用虚拟账号 |

### 请求示例

```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "app-spark", "bk_app_secret": "***"}' -d '{"operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/applications/demo-app/modules/default/deployments/22d0e9c8-9cfc-45a5-b5a8-718137c515db/interruptions/
```

### 返回结果示例

```json
{}
```

### 错误说明

| HTTP 状态码 | 场景 |
| ------ | ------ |
| 400 | 部署已处于结束状态，无法中断 |
| 400 | 任务正处于预备执行状态，无法中断，请稍候重试 |
| 400 | 该模块下没有对应的部署记录 |
| 403 | 调用方没有中断权限，或目标应用不归调用方管理 |
| 404 | 应用或模块不存在 |
