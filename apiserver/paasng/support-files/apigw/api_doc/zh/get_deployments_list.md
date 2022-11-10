### 资源描述
获取部署历史

### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 调用示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{你的appcode}/modules/{你的模块名}/deployments/lists/
```

### 返回结果
```json
{
    "count": 27,
    "next": "http://staging.bkpaas.example.com/backend/api/bkapps/applications/vision/modules/default/deployments/lists/?limit=12&offset=12",
    "previous": null,
    "results": [
        {
            "id": "36ef5721-7313-48fa-a59a-1dc47c585828",
            "status": "failed",
            "operator": {
                "id": "0227c0eb979e5289b5",
                "username": "admin",
                "provider_type": 2
            },
            "created": "2020-08-24 14:49:10",
            "deployment_id": "36ef5721-7313-48fa-a59a-1dc47c585828",
            "environment": "prod",
            "repo": {
                "source_type": "bk_gitlab",
                "type": "branch",
                "name": "master",
                "url": "http://git.example.com/v3-awesome-app.git",
                "revision": "141c46a87160afa4f33d280ddc368bf2c12fb5c7",
                "comment": ""
            }
        },
    ]
}
```

### 返回结果说明
<div class="model-box"><span class="model"><span class=""><span class="inner-object"><table class="model"><tbody><tr class="false"><td style="vertical-align: top; padding-right: 0.2em; font-weight: bold;"><!-- react-text: 5069 -->count<!-- /react-text --><span style="color: red;">*</span></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">integer</span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 5077 -->next<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span class="prop-format"><!-- react-text: 5083 -->($<!-- /react-text --><!-- react-text: 5084 -->uri<!-- /react-text --><!-- react-text: 5085 -->)<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5088 -->x-nullable<!-- /react-text --><!-- react-text: 5089 -->: <!-- /react-text --><!-- react-text: 5090 -->true<!-- /react-text --></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 5093 -->previous<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span class="prop-format"><!-- react-text: 5099 -->($<!-- /react-text --><!-- react-text: 5100 -->uri<!-- /react-text --><!-- react-text: 5101 -->)<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5104 -->x-nullable<!-- /react-text --><!-- react-text: 5105 -->: <!-- /react-text --><!-- react-text: 5106 -->true<!-- /react-text --></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em; font-weight: bold;"><!-- react-text: 5109 -->results<!-- /react-text --><span style="color: red;">*</span></td><td style="vertical-align: top;"><span class="model"><span class=""><span><span class="model"><span class=""><span><span class="model"><span class=""><span class="inner-object"><table class="model"><tbody><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 5150 -->id<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span class="prop-format"><!-- react-text: 5156 -->($<!-- /react-text --><!-- react-text: 5157 -->uuid<!-- /react-text --><!-- react-text: 5158 -->)<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5161 -->title<!-- /react-text --><!-- react-text: 5162 -->: <!-- /react-text --><!-- react-text: 5163 -->UUID<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5166 -->readOnly<!-- /react-text --><!-- react-text: 5167 -->: <!-- /react-text --><!-- react-text: 5168 -->true<!-- /react-text --></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 5171 -->status<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5178 -->title<!-- /react-text --><!-- react-text: 5179 -->: <!-- /react-text --><!-- react-text: 5180 -->部署状态<!-- /react-text --></span><span class="prop-enum"><!-- react-text: 5182 -->Enum:<!-- /react-text --><br><span class=""><span style="cursor: pointer;"><span class="model-toggle"></span></span><!-- react-text: 5231 -->[ <!-- /react-text --><!-- react-text: 5232 -->successful, failed, pending<!-- /react-text --><!-- react-text: 5233 --> ]<!-- /react-text --></span></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 5193 -->operator<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5200 -->title<!-- /react-text --><!-- react-text: 5201 -->: <!-- /react-text --><!-- react-text: 5202 -->Operator<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5205 -->readOnly<!-- /react-text --><!-- react-text: 5206 -->: <!-- /react-text --><!-- react-text: 5207 -->true<!-- /react-text --></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 5210 -->created<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span class="prop-format"><!-- react-text: 5216 -->($<!-- /react-text --><!-- react-text: 5217 -->date-time<!-- /react-text --><!-- react-text: 5218 -->)<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5221 -->title<!-- /react-text --><!-- react-text: 5222 -->: <!-- /react-text --><!-- react-text: 5223 -->Created<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5226 -->readOnly<!-- /react-text --><!-- react-text: 5227 -->: <!-- /react-text --><!-- react-text: 5228 -->true<!-- /react-text --></span></span></span></td></tr><tr>&nbsp;</tr></tbody></table></span></span></span></span></span></span></span></span></span></td></tr><tr>&nbsp;</tr></tbody></table></span></span></span></div>