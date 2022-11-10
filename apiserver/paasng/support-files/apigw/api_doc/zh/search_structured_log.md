### 资源描述

查询标准输出日志

### 认证方式

使用 Bearer 方式认证，具体的 token 请向管理员申请。

### 路径接口说明

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   是   |  应用 ID    |
|   module |   string     |   是   |  模块名称，如 "default" |

### 输入参数说明
| 参数名称              | 参数类型 | 必须 | 参数说明                                                             |
|-----------------------|----------|-----|------------------------------------------------------------------|
| private_token | string      | 否   | PaaS 平台分配的 token,当请求方的应用身份未被 PaaS 平台认证时必须提供|
| log_type              | string   | 是   | 日志类型，可选值："STRUCTURED" "STANDARD_OUTPUT" "INGRESS"，默认值为: "STRUCTURED" |
| time_range            | string   | 是   | 时间范围，可选值："5m" "1h" "3h" "6h" "12h" "1d" "3d" "7d" "customized" |
| start_time            | string   | 否   | time_range 为 "customized" 时需要填写                                |
| end_time              | string   | 否   | time_range 为 "customized" 时需要填写                |
| page              | int   | 是   | 大于 0 的整数               |
| page_size              | int   | 是   | 大于 0 的整数                |

**说明**：日志查询参数与 ES 的查询语法一致，可参考：https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html


### 返回结果

```javascript
{
    "code": 0,
    "data": {
        "page": {
            "page": 1,
            "page_size": 20,
            "total": 1
        },
        "logs": [
            {
                "region": "default",
                "app_code": "appid",
                "environment": "stag",
                "process_id": "web",
                "stream": "django",
                "message": "xxx",
                "detail": {
                    "json.asctime": "2022-04-15 17:21:33,770",
                    "json.funcName": "info",
                    "json.levelname": "INFO",
                    "json.lineno": 43,
                    "json.message": "xxx",
                    "json.process": 34,
                    "json.thread": 139842183358536
                },
                "ts": "2022-04-15 17:21:33"
            }
        ]
    }
}
```