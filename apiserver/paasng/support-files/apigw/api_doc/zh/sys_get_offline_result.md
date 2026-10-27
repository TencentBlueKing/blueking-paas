### 功能描述

以应用身份查询应用的下架任务结果。调用方须具备 AIDEV 或 AppSpark 系统角色，且只能查询自己管理的应用，否则返回 403：AIDEV 只能查询 AI Agent 应用，AppSpark 只能查询默认模块源码来源仍为 AppSpark 的应用，且只能查询默认模块在生产环境的下架任务。

返回结果与用户态接口 `get_offline_result` 一致。

### 请求参数

#### 1、路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | --- | -------- |
| app_code | string | 是 | 应用 ID，必须是调用方管理的应用 |
| module | string | 是 | 模块名称，如 "default" |
| offline_operation_id | string | 是 | 下架任务的 uuid |

#### 2、接口参数

暂无。

### 请求示例

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/offlines/4e69986f-00e8-41ad-bef9-8ac82201ae07/result/
```

### 返回结果示例

```json
{
    "id": "4e69986f-00e8-41ad-bef9-8ac82201ae07",
    "status": "successful",
    "operator": {
        "id": "0336c3a7948c4299b7",
        "username": "admin",
        "provider_type": 3,
        "avatar": ""
    },
    "created": "2024-08-19 11:30:26",
    "log": "offline succeeded.",
    "err_detail": null,
    "offline_operation_id": "4e69986f-00e8-41ad-bef9-8ac82201ae07",
    "environment": "stag",
    "repo": {
        "source_type": "ai_agent",
        "type": "package",
        "name": "0.0.5",
        "url": "",
        "revision": "0.0.5",
        "comment": ""
    }
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| id | string | UUID |
| status | string | 下线状态，可选值：successful, failed, pending |
| operator | object | 操作人 |
| created | string | 创建时间 |
| log | string | 下线日志 |
| err_detail | string | 下线异常原因 |
| offline_operation_id | string | 下线操作ID |
| environment | string | 环境名称 |
| repo | object | 仓库信息 |
