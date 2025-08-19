### 功能描述
查询可恢复的下架操作。可恢复的下架操作指当前被卡住的下线操作。

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | 是 | 应用 ID |
| module   | string | 是 | 模块名称，如 "default" |
| env | string | 是 | 环境名称，可选值 "stag" / "prod" |

#### 2、接口参数：
暂无。

### 请求示例

#### svn
```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{AppCode}}/modules/{{module_name}}/envs/{env:stag/prod}/offlines/resumable/
```

### 返回结果示例
#### 正常返回
当有可恢复的下线操作
```json
{
  "result": {
    "id": "--",
    "status": "successful",
    "operator": {
      "id": "--",
      "username": "--",
      "provider_type": 2
    },
    "created": datetime,
    "log": "try to stop process:web ...success to stop process: web\nall process stopped.\n",
    "err_detail": null,
    "offline_operation_id": "01e3617a-96b6-4bf3-98fb-1e27fc68c7ee",
    "environment": "stag",
    "repo": {
      "source_type": "--",
      "type": "--",
      "name": "--",
      "url": "--",
      "revision": "--",
      "comment": "--"
    }
  }
}
```

当没有可恢复的下线操作
```json
{}
```

### 返回结果参数说明

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| id | string | UUID |
| status | string | 下线状态，可选值：successful, failed, pending |
| operator | object | 操作人 |
| created | string | 创建时间 |
| log | string | 下线日志 |
| err_detail | string | 下线异常原因 |
| offline_operation_id | string | 下线操作ID |
| environment | string | 环境名称 |
| repo | object | 仓库信息 |

repo
| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| source_type | string | 源类型 |
| type | string | 类型 |
| name | string | 名称 |
| url | string | URL |
| revision | string | 版本 |
| comment | string | 备注 |