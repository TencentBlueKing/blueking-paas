### 资源描述

查询该时间区间内, 应用的总访问量。

### 输入参数说明

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | 是 | 应用ID(app id)，可以通过 蓝鲸开发者中心 -> 应用基本设置 -> 基本信息 -> 鉴权信息 获取 |
| app_secret | string | 否 | 安全秘钥(app secret)，可以通过 蓝鲸开发者中心 -> 应用基本设置 -> 基本信息 -> 鉴权信息 获取 |

### 路径参数

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | 是 | 应用 ID，如 "monitor" |
| module   | string | 是 | 模块名称，如 "default" |
| env   | string | 是 | 环境名，如 "stag"、"prod" |
| source_type   | string | 是 | 访问值来源，可选值 "ingress"（访问日志统计）, "user_tracker"（网站访问统计） |

### 参数说明

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| start_time   | date | 是 | 开始时间，如 "2020-05-20" |
| end_time   | date | 是 | 结束时间，如 "2020-05-22" |

### 调用示例

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{填写你的 AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/envs/{env}/analysis/m/{source_type}/metrics/total?start_time={start_time}&end_time={end_time}
```


### 返回结果

```javascirpt
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