### 功能描述
以应用身份创建 AppSpark 应用。调用方须具备 AppSpark 系统角色，其他角色调用返回 403。

创建的是标准云原生应用：不是插件应用，也不是 AI Agent 应用，会出现在用户的开发者中心应用列表中。应用同时建出预发布和生产两个环境，使用默认集群，访问控制保持关闭。默认模块的源码来源为 AppSpark，使用源码包部署，语言为 Python。

只创建、不部署，响应不含应用密钥。源码包与构建方式由后续的上传源码包接口提供。

管理员为请求中的 `operator`，必须是已在开发者中心注册的真实用户，不支持虚拟账号。管理员只在创建时设置，之后由用户在开发者中心自行管理成员。

用户在开发者中心将默认模块切换为代码仓库部署后，应用不再归 AppSpark 管理，AppSpark 后续调用相关接口会返回 403。

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：

| 字段 | 类型 | 是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| code | string | 是 | 应用 ID，按开发者中心标准规则校验：小写字母、数字、连接符，长度 3-20，全局唯一 |
| name | string | 是 | 应用名称 |
| operator | string | 是 | 应用管理员用户名，必须是已在开发者中心注册的用户 |
| app_tenant_mode | string | 否 | 应用租户模式 |
| app_tenant_id | string | 否 | 租户 ID，全租户应用则为空字符串 |

### 请求示例
```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "app-spark", "bk_app_secret": "***"}' -d '{"code": "demo-app", "name": "demo-app", "operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/app_spark/
```

### 返回结果示例
```
{
    "application": {
        "id": "479ca05c-962a-43d2-bd2c-af7735f2ede1",
        "name": "demo-app",
        "modules": [
            {
                "name": "default",
                "is_default": true,
                "language": "Python"
            }
        ],
        "code": "demo-app",
        "name_en": "demo-app",
        "type": "cloud_native",
        "is_plugin_app": false,
        "is_ai_agent_app": false,
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
