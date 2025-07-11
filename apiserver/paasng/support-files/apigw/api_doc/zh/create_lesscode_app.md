### 功能描述
创建蓝鲸运维开发平台应用

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：

| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| code | string | 是 | 应用编码 |
| name | string | 是 | 应用名称 |
| type | string | 是 | 应用类型，默认为 "default" |
| engine_enabled | boolean | 是 | 是否启用引擎 |
| engine_params | dict | 是 | 引擎参数 |

engine_params
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| source_origin    |  int |  是  | 源代码来源 |
| source_init_template |string  | 是 | 初始化模板，如 "nodejs_bk_magic_vue_spa" |

### 请求示例
```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"access_token": "your access_token", "bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' -d '{"code": "testappcode", "name": "testappcode", "type": "default", "engine_enabled": true, "engine_params": {"source_origin": 2, "source_init_template": "nodejs_bk_magic_vue_spa"}}' --insecure https://bkapi.example.com/api/bkpaas3/stag/bkapps/applications/lesscode/
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
                "language": "NodeJS",
            }
        ],
        "code": "testappcode",
        "name_en": "testappcode",
        "type": "default",
        "language": "NodeJS",
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