### 功能描述
以应用身份创建 AI Agent 应用。调用方须具备 AIDEV 系统角色。管理员为请求中的 `operator`，该用户必须已在开发者中心注册。应用 ID 必须以 `ai-` 开头。只创建、不部署，响应不含应用密钥。

支持与用户态相同的三种模式：固定模板包、git 仓库、外链 engineless。

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：

| 字段 | 类型 | 是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| code | string | 是 | 应用 ID，必须以 ai- 开头，长度 3-20 |
| name | string | 是 | 应用名称 |
| operator | string | 是 | 已在开发者中心注册的管理员用户名 |
| is_engineless | boolean | 否 | 是否创建为无引擎外链应用，默认 false |
| is_isolated | boolean | 否 | 是否部署到隔离环境，默认 false |
| source_config | object | 否 | git 源码配置，传入则使用 git 仓库部署 |
| bkapp_spec | object | 否 | 构建配置，与 source_config 一起使用时必填 |
| app_tenant_mode | string | 否 | 应用租户模式 |
| app_tenant_id | string | 否 | 租户 ID，全租户应用则为空字符串 |

### 请求示例
```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -d '{"code": "ai-demo", "name": "ai-demo", "operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/ai_agent/
```

### 返回结果示例
```
{
    "application": {
        "id": "479ca05c-962a-43d2-bd2c-af7735f2ede1",
        "name": "ai-demo",
        "modules": [
            {
                "name": "default",
                "is_default": true,
                "language": "Python"
            }
        ],
        "code": "ai-demo",
        "name_en": "ai-demo",
        "type": "cloud_native",
        "is_plugin_app": true,
        "is_ai_agent_app": true,
        "language": "Python",
        "is_active": true,
        "is_deleted": false,
        "last_deployed_date": null
    }
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| id | string | 应用 ID |
| name | string | 应用名称 |
| modules | list | 应用模块信息 |
| code | string | 应用编码 |
| name_en | string | 应用英文名称 |
| type | string | 应用类型 |
| is_plugin_app | boolean | 是否为插件应用 |
| is_ai_agent_app | boolean | 是否为 AI Agent 工具 |
| language | string | 应用语言 |
| is_active | boolean | 是否激活 |
| is_deleted | boolean | 是否已删除 |
| last_deployed_date | string | 最后部署日期 |


modules
| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| name | string | 模块名称 |
| is_default | boolean | 是否为默认模块 |
| language | string | 模块语言 |
