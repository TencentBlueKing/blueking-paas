### 功能描述

查询指定时间区间内，应用的总访问量。

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | 是 | 应用 ID，如 "monitor" |
| module   | string | 是 | 模块名称，如 "default" |
| env   | string | 是 | 环境名，如 "stag"、"prod" |
| source_type   | string | 是 | 访问值来源，可选值 "ingress"（访问日志统计）, "user_tracker"（网站访问统计） |

#### 2、接口参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| start_time   | date | 是 | 开始时间，如 "2020-05-20" |
| end_time   | date | 是 | 结束时间，如 "2020-05-22" |

### 请求示例

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/envs/{env}/analysis/m/{source_type}/metrics/total?start_time={start_time}&end_time={end_time}
```

### 返回结果示例

```javascript
{
  "site": {
    "type": "app",
    "name": "--",
    "id": 38
  },
  "result": {
    "results": {
      "pv": 100,
      "uv": 12
    },
    "source_type": "tracked_pv_by_site",
    "display_name": "站点总访问量"
  }
}
```

### 返回结果参数说明

| 字段 |   类型 |  描述 |
| ------ | ------ | ------ |
| site.type | string | 站点类型 |
| site.name | string | 站点名称 |
| site.id | int | 站点 ID |
| result.results.pv | int | 页面访问量 |
| result.results.uv | int | 用户访问量 |
| result.source_type | string | 访问值来源 |
| result.display_name | string | 显示名称 |