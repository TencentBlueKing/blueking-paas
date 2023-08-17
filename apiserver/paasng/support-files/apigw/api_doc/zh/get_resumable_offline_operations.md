### 功能描述
查询可恢复的下架操作

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

#### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

#### svn
```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{填写你的 AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{填写你的AppCode}}/modules/{{填写你的模块名}}/envs/{填写App部署环境:stag或prod}/offlines/resumable/
```

### 返回结果示例
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

### 返回结果参数说明

| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| id | string | 是 | UUID |
| status | string | 是 | 下线状态，可选值：successful, failed, pending |
| operator | string | 是 | Operator |
| created | string | 是 | Created |
| log | string | 是 | 下线日志 |
| err_detail | string | 是 | 下线异常原因 |
| offline_operation_id | string | 是 | 下线操作ID |
| environment | string | 是 | 环境名称 |
| repo | object | 是 | 仓库信息 |

repo
| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| source_type | string | 是 | 源类型 |
| type | string | 是 | 类型 |
| name | string | 是 | 名称 |
| url | string | 是 | URL |
| revision | string | 是 | 版本 |
| comment | string | 是 | 备注 |