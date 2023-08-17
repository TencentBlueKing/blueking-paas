### 功能描述
查询下架任务结果

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | 是 | 应用 ID |
| module   | string | 是 | 模块名称，如 "default" |
| offline_operation_id | string | 是 | 下架任务的uuid |

#### 2、接口参数：
暂无。


### 请求示例
```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{填写你的 AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{填写你的AppCode}}/modules/{{填写你的模块名}}/envs/{填写App部署环境:stag或prod}/offlines/{{offline_operation_id}}/result/
```

#### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 返回结果示例
```json
{
    "status": "str",
    "error_detail": "str",
    "logs": "str"
}
```

### 返回结果参数说明

| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| status | string | 是 | 下线任务状态(successful, pending或failed) |
| error_detail | string | 是 | 错误信息 |
| logs | string | 是 | 下线日志 |