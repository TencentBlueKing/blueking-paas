### 功能描述

以应用身份查询应用的部署任务结果。调用方须具备 AIDEV 或 AppSpark 系统角色，且只能查询自己管理的应用，否则返回 403：AIDEV 只能查询 AI Agent 应用，AppSpark 只能查询默认模块源码来源仍为 AppSpark 的应用，且只能查询默认模块在生产环境的部署。

返回结果与用户态接口 `get_deployment_result` 一致。部署成功时 `access_url` 为该环境的默认访问地址，可直接分享给用户。

### 请求参数

#### 1、路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | --- | -------- |
| app_code | string | 是 | 应用 ID，必须是调用方管理的应用 |
| module | string | 是 | 模块名称 |
| deployment_id | string | 是 | 部署任务 ID |

#### 2、接口参数

| 字段 | 类型 | 是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| include_ansi_codes | boolean | 否 | 是否保留日志中的 ANSI 转义序列，默认 false |

### 请求示例

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/deployments/22d0e9c8-9cfc-45a5-b5a8-718137c515db/result/
```

### 返回结果示例

```json
{
    "status": "failed",
    "logs": "\nProcfile error: ...",
    "error_detail": "Procfile error: ...",
    "error_tips": {
        "matched_solutions_found": false,
        "possible_reason": "暂时无法找到解决方案，请前往“标准输出日志”检查是否有异常",
        "helpers": [{
            "text": "日志查询",
            "link": "http://bkpaas.example.com/developer-center/apps/appid/default/log?tab=stream"
        }]
    },
    "access_url": null
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| status | string | 部署状态 |
| logs | string | 部署日志, 纯文本 |
| error_detail | string | 错误详情 |
| error_tips.matched_solutions_found | boolean | 是否有匹配的 tips |
| error_tips.possible_reason | string | 可能导致部署错误的原因 |
| error_tips.helpers | object | 辅助信息，包含文本和链接 |
| access_url | string | 部署成功时为该环境的默认访问地址（不含自定义域名）；其余状态，或环境当前未在运行时为 null |
