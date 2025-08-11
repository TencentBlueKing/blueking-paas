### 功能描述
创建 AI Agent 工具

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：

| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| code | string | 是 | 应用ID |
| name | string | 是 | 应用名称 |

### 请求示例
```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"access_token": "your access_token", "bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' -d '{"code": "testappcode", "name": "testappcode"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/bkapps/applications/ai_agent/
```

### 返回结果示例
```
{
    "application": {
        "id": "479ca05c-962a-43d2-bd2c-af7735f2ede1",
        "name": "testappcode",
        "modules": [
            {
                "name": "default",
                "is_default": true,
                "language": "Python",
            }
        ],
        "code": "testappcode",
        "name_en": "testappcode",
        "type": "cloud_native",
        "is_plugin_app": true,
        "is_ai_agent_app": true,
        "language": "Python",
        "is_active": true,
        "is_deleted": false,
        "last_deployed_date": null
    },
}
```

### 返回结果参数说明

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| id | string | 应用ID |
| name | string | 应用名称 |
| modules | list | 应用模块信息 |
| code | string | 应用编码 |
| name_en | string | 应用英文名称 |
| type | string | 应用类型 |
| is_plugin_app | boolean | 是否为插件应用 |
| is_ai_agent_app | boolean | 是否为 AI Agent 工具  |
| language | string | 应用语言 |
| is_active | boolean | 是否激活 |
| is_deleted | boolean | 是否已删除 |
| last_deployed_date | string | 最后部署日期 |


modules
| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| name | string | 模块名称 |
| is_default | boolean | 是否为默认模块 |
| language | string | 模块语言 |