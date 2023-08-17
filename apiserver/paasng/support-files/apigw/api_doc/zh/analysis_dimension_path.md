### 功能描述
查询该时间区间内, 应用按照路径维度分组聚合的访问数据

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
| ordering | string | 是 | 排序选项，推荐值 "-pv" |
| offset  | int | 否 | 分页参数，默认为 0 |
| limit   | int | 否 | 分页参数，默认为 30，最大 100 |

### 请求示例

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{填写你的 AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/envs/{env}/analysis/m/{source_type}/metrics/dimension/path?start_time={start_time}&end_time={end_time}&ordering=-pv
```

### 返回结果示例

```javascirpt
{
  "meta": {
    "schemas": {
      "resource_type": {
        "name": "path",
        "display_name": "访问路径"
      },
      "values_type": [{
          "name": "pv",
          "display_name": "访问量",
          "sortable": true
        },
        {
          "name": "uv",
          "display_name": "独立访客数",
          "sortable": true
        }
      ]
    },
    "pagination": {
      "total": 1
    }
  },
  "resources": [{
    // 路径名称
    "name": "/",
    "values": {
      "pv": 348,
      "uv": 48
    }
  }]
}
```

### 返回结果参数说明

| 字段 |   类型 |  描述 |
| ------ | ------ | ------ |
| meta | object | 元数据信息 |
| meta.schemas | object | 数据结构信息 |
| meta.schemas.resource_type | object | 资源类型信息 |
| meta.schemas.resource_type.name | string | 资源类型名称 |
| meta.schemas.resource_type.display_name | string | 资源类型显示名称 |
| meta.schemas.values_type | array | 值类型信息 |
| meta.schemas.values_type[].name | string | 值类型名称 |
| meta.schemas.values_type[].display_name | string | 值类型显示名称 |
| meta.schemas.values_type[].sortable | boolean | 是否可排序 |
| meta.pagination | object | 分页信息 |
| meta.pagination.total | int | 总数 |
| resources | array | 资源列表 |
| resources[].name | string | 路径名称 |
| resources[].values | object | 值信息 |
| resources[].values.pv | int | 访问量 |
| resources[].values.uv | int | 独立访客数 |