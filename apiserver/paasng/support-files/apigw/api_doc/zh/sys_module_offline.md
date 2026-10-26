### 功能描述

以应用身份将 AI Agent 应用模块从指定环境下架。调用方须具备 AIDEV 系统角色，且目标应用必须是 AI Agent 应用，否则返回 403。

下架逻辑与用户态接口 `module_offline` 一致，仅下架操作人由请求体中的 `operator` 指定。`operator` 只用于记录操作人，不校验其应用权限，也不受环境部署角色保护限制。

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
| operator | string | 是 | 下架操作人用户名，仅用于记录操作人，允许使用虚拟账号 |

### 请求示例

```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -d '{"operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/envs/stag/offlines/
```

### 返回结果示例

```json
{
    "offline_operation_id": "22d0e9c8-9cfc-45a5-b5a8-718137c515db"
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| offline_operation_id | string | 下架操作 ID |
