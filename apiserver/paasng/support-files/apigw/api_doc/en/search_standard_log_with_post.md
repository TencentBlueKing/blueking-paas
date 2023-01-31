### Description

Query application standard output log

### Input parameters

| Parameter Name | Parameter Location | Type | Required | Description |
|------|--------|------| :------: |-------------|
| end_time | `query` | string | | |
| log_type | `query` | string | | |
| scroll_id | `query` | string | | |
| start_time | `query` | string | | |
| time_range | `query` | string | yes | |
| data | `body` | SearchStandardLogWithPostBody | yes | |

### Responses
| Status Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Query successful |

### 响应

#### 200 - 查询成功
Status: OK

##### Schema

SearchStandardLogWithPostOKBody

##### 内联模型

**SearchStandardLogWithPostBody**


> 简化的 dsl 结构



**Properties**

| Name | Type | Required | Description | Example |
|------|------|:------------:|-------------|---------|
| query | SearchStandardLogWithPostParamsBodyQuery| yes | | |
| sort | interface{}| | 排序规则 | {'response_time': 'desc', 'other': 'asc'} |


**SearchStandardLogWithPostOKBody**



**Properties**

| Name | Type | Required | Description | Example |
|------|------|:------------:|-------------|---------|
| code | integer| | status code | |
| data | SearchStandardLogWithPostOKBodyData| | | |



**SearchStandardLogWithPostOKBodyData**
**Properties**

| Name | Type | Required | Description | Example |
|------|------|:------------:|-------------|---------|
| logs | []SearchStandardLogWithPostOKBodyDataLogsItems0| | | |
| scroll_id | string| | scroll_id for ES paging query | |
| total | integer| | number of logs | |


**SearchStandardLogWithPostOKBodyDataLogsItems0**



**Properties**

| Name | Type | Required | Description | Example |
|------|------|:------------:|-------------|---------|
| environment | string| | Deployment environment | |
| message | string| | log content | |
| pod_name | string| | instance name | |
| process_id | string| | application process | |
| timestamp | string| | log timestamp | |



**SearchStandardLogWithPostParamsBodyQuery**


> Simplified dsl-query structure
Currently only supports: query_string/terms two query methods
query_string: search using ES's query_string
terms: exact match (scenario filtered by field)



**Properties**

| Name | Type | Required | Description | Example |
|------|------|:------------:|-------------|---------|
| exclude | map of[]string| | negated terms, non-standard DSL | |
| query_string | string| | Search using `query_string` syntax | |
| terms | map of[]string| | Multi-value exact match | |
