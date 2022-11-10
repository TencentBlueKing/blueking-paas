### 资源描述
查询下架任务结果

### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 路径接口说明

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   是   |  应用 ID    |
|   module |   string     |   是   |  模块名称，如 "default" |
|   offline_operation_id | string |  是 | 下架任务的uuid |


### 调用示例
```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{填写你的 AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{填写你的AppCode}}/modules/{{填写你的模块名}}/envs/{填写App部署环境:stag或prod}/offlines/{{offline_operation_id}}/result/
```

### 返回结果
```json
{
    "status": "str",
    "error_detail": "str",
    "logs": "str"
}
```

### 返回结果说明
<table class="model"><tbody><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11430 -->status<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 11437 -->example<!-- /react-text --><!-- react-text: 11438 -->: <!-- /react-text --><!-- react-text: 11439 -->failed<!-- /react-text --></span><div class="markdown"><p>下线任务状态(successful, pending或failed)</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11443 -->error_detail<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 11450 -->example<!-- /react-text --><!-- react-text: 11451 -->: <!-- /react-text --><!-- react-text: 11452 -->failed<!-- /react-text --></span><div class="markdown"><p>错误信息</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11456 -->logs<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 11463 -->example<!-- /react-text --><!-- react-text: 11464 -->: <!-- /react-text --><!-- react-text: 11465 -->Starting stop `web` process<!-- /react-text --></span><div class="markdown"><p>下线日志</p>
</div></span></span></td></tr><tr>&nbsp;</tr></tbody></table>