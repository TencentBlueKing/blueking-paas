### 功能描述

以应用身份部署 AI Agent 应用到指定环境。调用方须具备 AIDEV 系统角色，且目标应用必须是 AI Agent 应用，否则返回 403。

部署逻辑与用户态接口 `deploy_with_module` 一致，仅部署操作人由请求体中的 `operator` 指定。`operator` 只用于记录操作人，不校验其应用权限，也不受环境部署角色保护限制。应用态部署不支持构建调试（`advanced_options.debug_enabled`）。

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
| version_type | string | 是 | 版本类型，源码包部署时传 package |
| version_name | string | 是 | 版本名称，源码包部署时为源码包版本号 |
| revision | string | 否 | 版本信息，源码包部署时为源码包版本号 |
| operator | string | 是 | 部署操作人用户名，仅用于记录操作人，允许使用虚拟账号 |
| advanced_options | object | 否 | 高级选项，与用户态部署接口一致，不支持 debug_enabled |

### 请求示例

```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -d '{"version_type": "package", "version_name": "0.0.5", "revision": "0.0.5", "operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/envs/stag/deployments/
```

### 返回结果示例

```json
{
    "stream_url": "/streams/22d0e9c8-9cfc-45a5-b5a8-718137c515db",
    "deployment_id": "22d0e9c8-9cfc-45a5-b5a8-718137c515db"
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| stream_url | string | 部署日志输出流 ID |
| deployment_id | string | 部署操作 ID |
