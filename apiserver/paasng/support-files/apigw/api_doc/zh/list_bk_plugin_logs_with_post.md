### 功能描述
查询某个“蓝鲸插件”类型应用的日志，仅供内部系统使用。该接口默认检索最近 14 天范围内的所有日志，每次返回 200 条，暂不支持定制。

### 请求参数

#### 1、路径参数：
|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| code | string | 是 | 位置参数，待查询插件的 code |

#### 2、接口参数：
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| scroll_id | string | 否 | 用于滚动翻页的标识字段 |
| trace_id | string | 是 | 用于过滤日志的 `trace_id` 标识符 |

### 请求示例
```bash
curl -X POST -H 'X-Bkapi-Authorization: {"bk_app_code": "bk_apigw_test", "bk_app_secret": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/system/bk_plugins/appid1/logs/?trace_id=1111'
```

### 返回结果示例
#### 正常返回
```javascript
{
    "logs": [
        {
            "timestamp": 1724152930,
            "message": "[execute] plugin execute failed",
            "raw": {
                "otelServiceName": null,
                "pathname": "/app/.heroku/python/lib/python3.6/site-packages/bk_plugin_framework/runtime/executor.py",
                "otelTraceID": null,
                "otelSpanID": null,
                "message": "[execute] plugin execute failed",
                "__ext_json.lineno": 99,
                "__ext_json.process": 6368,
                "__ext_json.thread": 139939413554944,
                "__ext_json.trace_id": "88d9254695094eb09851f261cda8d5e6",
                "__ext_json.exc_info": "Traceback (most recent call last):\n  File ...",
                "funcName": "execute",
                "levelname": "ERROR",
                "region": "ieod",
                "app_code": "bkchat-sops",
                "module_name": "default",
                "environment": "prod",
                "process_id": "web",
                "pod_name": "bkapp-bkchat-sops-prod--web-865dddfdcc-fxg8p",
                "stream": null,
                "ts": "2024-08-20 19:22:10",
                "json.levelname": "ERROR",
                "json.funcName": "execute",
                "json.message": "[execute] plugin execute failed"
            },
            "detail": {
                "otelServiceName": null,
                "pathname": "/app/.heroku/python/lib/python3.6/site-packages/bk_plugin_framework/runtime/executor.py",
                "otelTraceID": null,
                "otelSpanID": null,
                "message": "[execute] plugin execute failed",
                "__ext_json.lineno": 99,
                "__ext_json.process": 6368,
                "__ext_json.thread": 139939413554944,
                "__ext_json.trace_id": "88d9254695094eb09851f261cda8d5e6",
                "__ext_json.exc_info": "Traceback (most recent call last):\n ...",
                "funcName": "execute",
                "levelname": "ERROR",
                "region": "ieod",
                "app_code": "bkchat-sops",
                "module_name": "default",
                "environment": "prod",
                "process_id": "web",
                "pod_name": "bkapp-bkchat-sops-prod--web-865dddfdcc-fxg8p",
                "stream": null,
                "ts": "2024-08-20 19:22:10",
                "json.levelname": "ERROR",
                "json.funcName": "execute",
                "json.message": "[execute] plugin execute failed"
            },
            "plugin_code": "bkchat-sops",
            "environment": "prod",
            "process_id": "web",
            "stream": "<object object at 0x7f144e63a540>",
            "ts": "2024-08-20 19:22:10"
        }
    ],
    "total": 11,
    "dsl": "{\"query\": {\"bool\": {\"filter\": ...",
    "scroll_id": "FGluY2x1ZGVfY29udG..."
}
```

#### 异常返回
```
{
    "code": "VALIDATION_ERROR",
    "detail": "trace_id: 该字段是必填项。",
    "fields_detail": {
        "trace_id": [
            "该字段是必填项。"
        ]
    }
}
```

### 返回结果参数说明
|   参数名称   |  参数类型  |           参数说明             |
| ------------ | ---------- | ------------------------------ |
|  scroll_id    | str | 翻页标识字段，获取下一页时传入该值 |
|  logs         | list[objects] | 日志对象列表，按创建时间从新到旧排序 |
|  total        | int | 日志总数 |
| dsl           | string         | DSL查询语句 |

`logs` 内对象字段说明：

|   参数名称   |  参数类型  |           参数说明             |
| ------------ | ---------- | ------------------------------ |
|  plugin_code | str | 插件标识符 |
|  environment | str | 产生日志的部署环境，`stag` -> 预发布环境，`prod` -> 生产环境 |
|  message       | str | 日志信息 |
| raw            | object         | 原生log  |
|  detail        | object         | 结构化日志详情 |
| process_id     | string         | 进程唯一类型  |
| stream         | string         | 流对象 |
| ts             | string         | 时间戳 |

**注意**：`detail.json.trace_id` 字段里，有用来标示字段高亮的 `[bk-mark]...[/bk-mark]` 标记字符，如需用于前端展示，请妥善处理。