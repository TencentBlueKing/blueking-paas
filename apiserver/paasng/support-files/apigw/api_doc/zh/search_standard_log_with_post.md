### 描述

查询应用标准输出日志

### 输入参数

| 参数名称 | 参数位置 | 类型 | 必选 | 描述 |
|------|--------|------| :------: |-------------|
| end_time | `query` | string |  |  |
| log_type | `query` | string |  |  |
| scroll_id | `query` | string |  |  |
| start_time | `query` | string |  |  |
| time_range | `query` | string | 是 |  |
| data | `body` | SearchStandardLogWithPostBody | 是 |  |

### 所有响应
| 状态码 | 状态 | 描述 |
|------|--------|-------------|
| 200 | OK | 查询成功 |

### 响应

#### 200 - 查询成功
Status: OK

##### Schema

SearchStandardLogWithPostOKBody

##### 内联模型

**SearchStandardLogWithPostBody**


> 简化的 dsl 结构



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| query | SearchStandardLogWithPostParamsBodyQuery| 是 |  |  |
| sort | interface{}|  | 排序，e.g. {'response_time': 'desc', 'other': 'asc'} |  |



**SearchStandardLogWithPostOKBody**



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| code | integer|  | 状态码 |  |
| data | SearchStandardLogWithPostOKBodyData|  |  |  |



**SearchStandardLogWithPostOKBodyData**


> 返回内容



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| logs | []SearchStandardLogWithPostOKBodyDataLogsItems0|  |  |  |
| scroll_id | string|  | ES 分页查询用的 scroll_id |  |
| total | integer|  | 日志数量 |  |



**SearchStandardLogWithPostOKBodyDataLogsItems0**



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| environment | string|  | 部署环境 |  |
| message | string|  | 日志内容 |  |
| pod_name | string|  | 实例名 |  |
| process_id | string|  | 应用进程 |  |
| timestamp | string|  | 日志时间戳 |  |



**SearchStandardLogWithPostParamsBodyQuery**


> 简化的 dsl-query 结构
目前只支持: query_string/terms 两种查询方式
query_string: 使用 ES 的 query_string 搜索
terms: 精准匹配(根据 field 过滤 的场景)



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| exclude | map of[]string|  | terms取反, 非标准 DSL |  |
| query_string | string|  | 使用 `query_string` 语法进行搜索 |  |
| terms | map of[]string|  | 多值精准匹配 |  |