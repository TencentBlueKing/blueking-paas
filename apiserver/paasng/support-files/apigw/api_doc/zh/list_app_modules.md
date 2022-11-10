### 资源描述
查看应用下所有的模块

### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 调用示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/
```

### 请求参数说明
<table class="parameters"><thead><tr><th class="col_header parameters-col_name">Name</th><th class="col_header parameters-col_description">Description</th></tr></thead><tbody><tr data-param-name="code" data-param-in="url"><td class="parameters-col_name"><div class="parameter__name"><!-- react-text: 11565 -->code<!-- /react-text --></div><div class="parameter__type"><!-- react-text: 11567 -->string<!-- /react-text --></div><div class="parameter__deprecated"></div><div class="parameter__in"><!-- react-text: 11570 -->(<!-- /react-text --><!-- react-text: 11571 -->url<!-- /react-text --><!-- react-text: 11572 -->)<!-- /react-text --></div></td><td class="parameters-col_description"><div class="markdown"><p>应用编码</p>
</div><input type="text" class="" title="" placeholder="code - 应用编码" disabled="" value=""></td></tr><tr data-param-name="source_origin" data-param-in="query"><td class="parameters-col_name"><div class="parameter__name"><!-- react-text: 11579 -->source_origin<!-- /react-text --></div><div class="parameter__type"><!-- react-text: 11581 -->int<!-- /react-text --></div><div class="parameter__deprecated"></div><div class="parameter__in"><!-- react-text: 11584 -->(<!-- /react-text --><!-- react-text: 11585 -->query<!-- /react-text --><!-- react-text: 11586 -->)<!-- /react-text --></div></td><td class="parameters-col_description"><div class="markdown"><p>源码来源，目前展示所有来源。支持 <code>1</code>（代码仓库）、<code>2</code>（蓝鲸 LessCode）</p>
</div><input type="text" class="" title="" placeholder="source_origin - 源码来源，目前展示所有来源。支持 `1`（代码仓库）、`2`（蓝鲸 LessCode）" disabled="" value=""></td></tr></tbody></table>

### 返回结果
```json
[
    {
        "id": "4fd1848d-cd89-4bdf-ae90-423eeaccf874",
        "name": "default",
        "source_origin": 2,
        "is_default": true
    }
]
```

### 返回结果说明
<table class="model"><tbody><tr style="color: rgb(102, 102, 102); font-weight: normal;"><td style="font-weight: bold;">description:</td><td><div class="markdown"><p>应用模块（精简）</p>
</div></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 12937 -->id<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><div class="markdown"><p>模块 UUID</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 12945 -->name<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><div class="markdown"><p>模块名称，比如 default</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 12953 -->is_default<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">bool</span><div class="markdown"><p>是否为默认模块</p>
</div></span></span></td></tr><tr>&nbsp;</tr></tbody></table>