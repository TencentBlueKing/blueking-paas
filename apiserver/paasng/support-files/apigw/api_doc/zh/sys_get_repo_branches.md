### 功能描述

以应用身份查询 AI Agent 应用模块的代码分支仓库。

返回结构与用户态接口 `get_repo_branches` 一致。

#### 租户说明

应用态接口不依赖用户登录态，租户通过 `X-Bk-Tenant-Id` 请求头传递：

- 全租户应用（`app_tenant_mode` 为 `global`）对所有租户可用；
- 单租户应用仅在其 `app_tenant_id` 对应租户下可用，其余租户返回 403 `APP_TENANT_MISMATCH`；
- 未开启多租户模式时忽略该请求头。

### 请求参数

#### 1、路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| --- | --- | --- | --- |
| app_code | string | 是 | 应用 ID，必须是 AI Agent 应用 |
| module | string | 是 | 模块名称，如 "default" |

#### 2、接口参数

无。

### 请求示例

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -H 'X-Bk-Tenant-Id: default' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/repo/branches/
```

### 返回结果示例

```json
{
    "results": [
        {
            "name": "master",
            "type": "branch",
            "display_type": "branch",
            "revision": "31736e690ba0bfa7a81d3730ed6544b3566b3f19",
            "url": "http://git.example.com/ai-demo.git",
            "last_update": "2024-09-10 16:48:24",
            "message": "init repo",
            "extra": {}
        }
    ]
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| results | list | 分支与标签列表 |
| results[].name | string | 分支名称 |
| results[].type | string | 版本类型（branch / tag） |
| results[].display_type | string | 展示类型（branch / tag），S-Mart 应用的 tag 展示为 image |
| results[].revision | string | 最新提交哈希 |
| results[].url | string | 仓库地址 |
| results[].last_update | string | 最后更新时间 |
| results[].message | string | 最后提交信息 |
| results[].extra | object | 额外信息 |
