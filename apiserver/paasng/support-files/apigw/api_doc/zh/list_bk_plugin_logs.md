### 功能描述
查询某个“蓝鲸插件”类型应用的日志，仅供内部系统使用。该接口默认检索最近 14 天范围内的所有日志，每次返回 200 条，暂不支持定制。

### 请求参数

#### 1、路径参数：
|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| code | string | 否 | 位置参数，待查询插件的 code |

#### 2、接口参数：
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| scroll_id | string | 否 | 用于滚动翻页的标识字段 |
| trace_id | string | 是 | 用于过滤日志的 `trace_id` 标识符 |

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "bk_apigw_test", "bk_app_secret": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/system/bk_plugins/appid1/logs/?trace_id=1111'
```

### 返回结果示例
```javascript
{
    "scroll_id": "FGluY2x1Z...",
    "logs": [
        {
            "plugin_code": "bk-plugin-demo",
            "environment": "stag",
            "process_id": "web",
            "stream": "component",
            "message": "A log message",
            "detail": {
                "json.asctime": "2021-08-26 11:06:44,325",
                "json.funcName": "foo_function",
                "json.levelname": "INFO",
                "json.lineno": 16,
                "json.message": "A log message",
                "json.pathname": "/app/foo.py",
                "json.process": 30,
                "json.thread": 140625517852824,
                "json.trace_id": "[bk-mark]2c1f0c1ae2c84505b1ed14ad8e924a12[/bk-mark]"
            },
            "ts": "2021-08-26 11:06:44"
        }
    ],
    "total": 1
}
```

### 返回结果参数说明
|   参数名称   |  参数类型  |           参数说明             |
| ------------ | ---------- | ------------------------------ |
|  scroll_id | str | 翻页标识字段，获取下一页时传入该值 |
|  logs | list[objects] | 日志对象列表，按创建时间从新到旧排序 |
|  total | int | 日志总数 |

`logs` 内对象字段说明：

|   参数名称   |  参数类型  |           参数说明             |
| ------------ | ---------- | ------------------------------ |
|  plugin_code | str | 插件标识符 |
|  environment | str | 产生日志的部署环境，`stag` -> 预发布环境，`prod` -> 生产环境 |
|  message | str | 日志信息 |
|  detail | object | 结构化日志详情 |

**注意**：`detail.json.trace_id` 字段里，有用来标示字段高亮的 `[bk-mark]...[/bk-mark]` 标记字符，如需用于前端展示，请妥善处理。