### 资源描述
查询部署日志

### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 调用示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}' http://bkapi.example.com/api/bkpaas3/prod/streams/{channel_id}/history_events
```

### ### 请求参数说明
<table class="parameters"><thead><tr><th class="col_header parameters-col_name">Name</th><th class="col_header parameters-col_description">Description</th></tr></thead><tbody><tr data-param-name="last_event_id" data-param-in="query"><td class="parameters-col_name"><div class="parameter__name"><!-- react-text: 6497 -->last_event_id<!-- /react-text --></div><div class="parameter__type"><!-- react-text: 6499 -->integer<!-- /react-text --></div><div class="parameter__deprecated"></div><div class="parameter__in"><!-- react-text: 6502 -->(<!-- /react-text --><!-- react-text: 6503 -->query<!-- /react-text --><!-- react-text: 6504 -->)<!-- /react-text --></div></td><td class="parameters-col_description"><div class="markdown"><p>最后一个事件id</p>
</div><div class="parameter__default markdown"><p><i>Default value</i> : 0</p>
</div><input type="text" class="" title="" placeholder="last_event_id - 最后一个事件id" value="0" disabled=""></td></tr><tr data-param-name="channel_id" data-param-in="path"><td class="parameters-col_name"><div class="parameter__name required"><!-- react-text: 6512 -->channel_id<!-- /react-text --><span style="color: red;">&nbsp;*</span></div><div class="parameter__type"><!-- react-text: 6515 -->string<!-- /react-text --></div><div class="parameter__deprecated"></div><div class="parameter__in"><!-- react-text: 6518 -->(<!-- /react-text --><!-- react-text: 6519 -->path<!-- /react-text --><!-- react-text: 6520 -->)<!-- /react-text --></div></td><td class="parameters-col_description"><input type="text" class="" title="" placeholder="channel_id" value="即deployment_id" disabled=""></td></tr></tbody></table>

### 返回结果
```json
[
  {
    "id": 1,
    "event": "init",
    "data": ""
  },
  {
    "id": 2,
    "event": "title",
    "data": "正在尝试创建 CI 相关资源"
  },
  ...
  {
    "id": 10,
    "event": "msg",
    "data": "{\"line\": \"Preparing to build bkapp-v200115-new-app-stag ...\", \"stream\": \"STDOUT\"}"
  },
  ...
  {
    "id": 136,
    "event": "msg",
    "data": "{\"line\": \"> web instance \\\"5f265pz\\\" is ready [\\u2705]\", \"stream\": \"StreamType.STDOUT\"}"
  },
  {
    "id": 137,
    "event": "title",
    "data": "项目部署成功"
  },
  {
    "id": 138,
    "event": "close",
    "data": ""
  }
]
```

### 返回结果说明
<table class="model"><tbody><tr class="false"><td style="vertical-align: top; padding-right: 0.2em; font-weight: bold;"><!-- react-text: 6574 -->id<!-- /react-text --><span style="color: red;">*</span></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">integer</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 6582 -->title<!-- /react-text --><!-- react-text: 6583 -->: <!-- /react-text --><!-- react-text: 6584 -->Id<!-- /react-text --></span><div class="markdown"><p>事件id</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em; font-weight: bold;"><!-- react-text: 6588 -->event<!-- /react-text --><span style="color: red;">*</span></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 6596 -->title<!-- /react-text --><!-- react-text: 6597 -->: <!-- /react-text --><!-- react-text: 6598 -->Event<!-- /react-text --></span><div class="markdown"><p>事件类型</p>
</div><span class="prop-enum"><!-- react-text: 6601 -->Enum:<!-- /react-text --><br><span class=""><span style="cursor: pointer;"><span class="model-toggle"></span></span><!-- react-text: 6724 -->[ <!-- /react-text --><!-- react-text: 6725 -->init, close, msg, title<!-- /react-text --><!-- react-text: 6726 --> ]<!-- /react-text --></span></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em; font-weight: bold;"><!-- react-text: 6612 -->data<!-- /react-text --><span style="color: red;">*</span></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 6620 -->title<!-- /react-text --><!-- react-text: 6621 -->: <!-- /react-text --><!-- react-text: 6622 -->Data<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 6625 -->minLength<!-- /react-text --><!-- react-text: 6626 -->: <!-- /react-text --><!-- react-text: 6627 -->1<!-- /react-text --></span><div class="markdown"><p>事件内容</p>
</div></span></span></td></tr><tr>&nbsp;</tr></tbody></table>