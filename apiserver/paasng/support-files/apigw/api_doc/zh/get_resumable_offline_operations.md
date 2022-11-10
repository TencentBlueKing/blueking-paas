### 资源描述
查询可恢复的下架操作

### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 路径接口说明

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   是   |  应用 ID    |
|   module |   string     |   是   |  模块名称，如 "default" |
|   env | string |  是 | 环境名称，可选值 "stag" / "prod" |

### 调用示例

#### svn
```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{填写你的 AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{填写你的AppCode}}/modules/{{填写你的模块名}}/envs/{填写App部署环境:stag或prod}/offlines/resumable/
```

### 返回结果
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

### 返回结果说明
<table class="model"><tbody><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 5762 -->id<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span class="prop-format"><!-- react-text: 5768 -->($<!-- /react-text --><!-- react-text: 5769 -->uuid<!-- /react-text --><!-- react-text: 5770 -->)<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5773 -->title<!-- /react-text --><!-- react-text: 5774 -->: <!-- /react-text --><!-- react-text: 5775 -->UUID<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5778 -->readOnly<!-- /react-text --><!-- react-text: 5779 -->: <!-- /react-text --><!-- react-text: 5780 -->true<!-- /react-text --></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 5783 -->status<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5790 -->title<!-- /react-text --><!-- react-text: 5791 -->: <!-- /react-text --><!-- react-text: 5792 -->下线状态<!-- /react-text --></span><span class="prop-enum"><!-- react-text: 5794 -->Enum:<!-- /react-text --><br><span class=""><span style="cursor: pointer;"><span class="model-toggle"></span></span><!-- react-text: 5877 -->[ <!-- /react-text --><!-- react-text: 5878 -->successful, failed, pending<!-- /react-text --><!-- react-text: 5879 --> ]<!-- /react-text --></span></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 5805 -->operator<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5812 -->title<!-- /react-text --><!-- react-text: 5813 -->: <!-- /react-text --><!-- react-text: 5814 -->Operator<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5817 -->readOnly<!-- /react-text --><!-- react-text: 5818 -->: <!-- /react-text --><!-- react-text: 5819 -->true<!-- /react-text --></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 5822 -->created<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span class="prop-format"><!-- react-text: 5828 -->($<!-- /react-text --><!-- react-text: 5829 -->date-time<!-- /react-text --><!-- react-text: 5830 -->)<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5833 -->title<!-- /react-text --><!-- react-text: 5834 -->: <!-- /react-text --><!-- react-text: 5835 -->Created<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5838 -->readOnly<!-- /react-text --><!-- react-text: 5839 -->: <!-- /react-text --><!-- react-text: 5840 -->true<!-- /react-text --></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 5843 -->log<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5850 -->title<!-- /react-text --><!-- react-text: 5851 -->: <!-- /react-text --><!-- react-text: 5852 -->下线日志<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5855 -->x-nullable<!-- /react-text --><!-- react-text: 5856 -->: <!-- /react-text --><!-- react-text: 5857 -->true<!-- /react-text --></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 5860 -->err_detail<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5867 -->title<!-- /react-text --><!-- react-text: 5868 -->: <!-- /react-text --><!-- react-text: 5869 -->下线异常原因<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5872 -->x-nullable<!-- /react-text --><!-- react-text: 5873 -->: <!-- /react-text --><!-- react-text: 5874 -->true<!-- /react-text --></span></span></span></td></tr><tr>&nbsp;</tr></tbody></table>