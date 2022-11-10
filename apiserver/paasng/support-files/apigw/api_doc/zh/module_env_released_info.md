### 资源描述
查询应用模块环境部署信息

### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 调用示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{code}/modules/{module_name}/envs/{environment}/released_info/
```

### 请求参数说明
<table class="parameters"><thead><tr><th class="col_header parameters-col_name">Name</th><th class="col_header parameters-col_description">Description</th></tr></thead><tbody><tr data-param-name="code" data-param-in="path"><td class="parameters-col_name"><div class="parameter__name required"><!-- react-text: 10603 -->code<!-- /react-text --><span style="color: red;">&nbsp;*</span></div><div class="parameter__type"><!-- react-text: 10606 -->string<!-- /react-text --></div><div class="parameter__deprecated"></div><div class="parameter__in"><!-- react-text: 10609 -->(<!-- /react-text --><!-- react-text: 10610 -->path<!-- /react-text --><!-- react-text: 10611 -->)<!-- /react-text --></div></td><td class="parameters-col_description"><input type="text" class="" title="" placeholder="code" value="" disabled=""></td></tr><tr data-param-name="environment" data-param-in="path"><td class="parameters-col_name"><div class="parameter__name required"><!-- react-text: 10617 -->environment<!-- /react-text --><span style="color: red;">&nbsp;*</span></div><div class="parameter__type"><!-- react-text: 10620 -->string<!-- /react-text --></div><div class="parameter__deprecated"></div><div class="parameter__in"><!-- react-text: 10623 -->(<!-- /react-text --><!-- react-text: 10624 -->path<!-- /react-text --><!-- react-text: 10625 -->)<!-- /react-text --></div></td><td class="parameters-col_description"><input type="text" class="" title="" placeholder="environment" value="" disabled=""></td></tr><tr data-param-name="module_name" data-param-in="path"><td class="parameters-col_name"><div class="parameter__name required"><!-- react-text: 10631 -->module_name<!-- /react-text --><span style="color: red;">&nbsp;*</span></div><div class="parameter__type"><!-- react-text: 10634 -->string<!-- /react-text --></div><div class="parameter__deprecated"></div><div class="parameter__in"><!-- react-text: 10637 -->(<!-- /react-text --><!-- react-text: 10638 -->path<!-- /react-text --><!-- react-text: 10639 -->)<!-- /react-text --></div></td><td class="parameters-col_description"><input type="text" class="" title="" placeholder="module_name" value="" disabled=""></td></tr></tbody></table>

### 返回结果
```json
{
  "deployment": {
    "id": "--",
    "status": "--",
    "operator": {
      "id": "--",
      "username": "--",
      "provider_type": 2
    },
    "created": "--",
    "deployment_id": "--",
    "environment": "--",
    "repo": {
      "source_type": "--",
      "type": "--",
      "name": "--",
      "url": "--",
      "revision": "--",
      "comment": ""
    }
  },
  "exposed_link": {
    "url": "--"
  }
}
```