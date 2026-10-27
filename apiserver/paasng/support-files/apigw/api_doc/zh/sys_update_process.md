### 功能描述

以应用身份启动、停止 AI Agent 应用进程或调整进程副本数（用于企微 wxaibot 进程管理）。调用方须具备 AIDEV 系统角色，且目标应用必须是 AI Agent 应用，否则返回 403。

### 请求参数

#### 1、路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | --- | -------- |
| app_code | string | 是 | 应用 ID，必须是 AI Agent 应用 |
| module | string | 是 | 模块名称，如 "default" |
| env | string | 是 | 环境名称，可选值 "stag" / "prod" |

#### 2、接口参数

| 字段 | 类型 | 是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| operate_type | string | 是 | 操作类型，可选值：start / stop / scale |
| process_type | string | 是 | 进程名，如 web |
| target_replicas | integer | 否 | 目标副本数，`operate_type` 为 `scale` 且未开启自动扩缩容时必填 |
| autoscaling | boolean | 否 | 是否开启自动扩缩容，默认 false |
| scaling_config | object | 否 | 自动扩缩容配置，开启自动扩缩容时必填 |
| operator | string | 是 | 操作人用户名，仅用于记录操作人，允许使用虚拟账号 |

### 请求示例

```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -d '{"operate_type": "scale", "process_type": "web", "target_replicas": 2, "operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/envs/stag/processes/
```

### 返回结果示例

```json
{
    "target_replicas": 2,
    "target_status": "start"
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| target_replicas | integer | 操作后的目标副本数 |
| target_status | string | 操作后的目标状态，start 表示运行中，stop 表示已停止 |
