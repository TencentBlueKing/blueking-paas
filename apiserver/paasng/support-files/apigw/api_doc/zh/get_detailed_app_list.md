### 资源描述
获取 App 详细信息

### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 调用示例
```bash
curl -X GET -H 'Accept: */*' -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}' http://bkapi.example.com/api/bkpaas3/bkapps/applications/lists/detailed
```

### 请求参数说明

<table class="sc-dxgOiQ eCjbJc"><tbody><tr><td class="sc-cSHVUG sc-chPdSV ffryYJ" kind="field" title="limit"><span class="sc-kGXeez bcLONg"></span>limit</td><td class="sc-kgoBCf kGwPhO"><div><div><span class="sc-cHGsZl sc-TOsTZ fKyGWc"></span><span class="sc-cHGsZl sc-kgAjT hqYVjx">number</span></div> <div><div class="sc-jWBwVP sc-iRbamj gDsWLk"><p>结果数量</p>
</div></div></div></td></tr><tr><td class="sc-cSHVUG sc-chPdSV ffryYJ" kind="field" title="offset"><span class="sc-kGXeez bcLONg"></span>offset</td><td class="sc-kgoBCf kGwPhO"><div><div><span class="sc-cHGsZl sc-TOsTZ fKyGWc"></span><span class="sc-cHGsZl sc-kgAjT hqYVjx">number</span></div> <div><div class="sc-jWBwVP sc-iRbamj gDsWLk"><p>翻页跳过数量</p>
</div></div></div></td></tr><tr><td class="sc-cSHVUG sc-chPdSV ffryYJ" kind="field" title="exclude_collaborated"><span class="sc-kGXeez bcLONg"></span>exclude_collaborated</td><td class="sc-kgoBCf kGwPhO"><div><div><span class="sc-cHGsZl sc-TOsTZ fKyGWc"></span><span class="sc-cHGsZl sc-kgAjT hqYVjx">boolean</span></div><div><span class="sc-cHGsZl lpeYvY"> Default: </span> <span class="sc-cHGsZl sc-jbKcbu kTVySD">false</span></div> <div><div class="sc-jWBwVP sc-iRbamj gDsWLk"><p>是否排除拥有协作者权限的应用，默认不排除。如果为 true，意为只返回我创建的</p>
</div></div></div></td></tr><tr><td class="sc-cSHVUG sc-chPdSV ffryYJ" kind="field" title="include_inactive"><span class="sc-kGXeez bcLONg"></span>include_inactive</td><td class="sc-kgoBCf kGwPhO"><div><div><span class="sc-cHGsZl sc-TOsTZ fKyGWc"></span><span class="sc-cHGsZl sc-kgAjT hqYVjx">boolean</span></div><div><span class="sc-cHGsZl lpeYvY"> Default: </span> <span class="sc-cHGsZl sc-jbKcbu kTVySD">false</span></div> <div><div class="sc-jWBwVP sc-iRbamj gDsWLk"><p>是否包含已下架应用，默认不包含</p>
</div></div></div></td></tr><tr><td class="sc-cSHVUG sc-chPdSV ffryYJ" kind="field" title="language"><span class="sc-kGXeez bcLONg"></span>language</td><td class="sc-kgoBCf kGwPhO"><div><div><span class="sc-cHGsZl sc-TOsTZ fKyGWc"></span><span class="sc-cHGsZl sc-kgAjT hqYVjx">string</span></div> <div><div class="sc-jWBwVP sc-iRbamj gDsWLk"><p>APP 编程语言</p>
</div></div></div></td></tr><tr><td class="sc-cSHVUG sc-chPdSV ffryYJ" kind="field" title="search_term"><span class="sc-kGXeez bcLONg"></span>search_term</td><td class="sc-kgoBCf kGwPhO"><div><div><span class="sc-cHGsZl sc-TOsTZ fKyGWc"></span><span class="sc-cHGsZl sc-kgAjT hqYVjx">string</span></div> <div><div class="sc-jWBwVP sc-iRbamj gDsWLk"><p>搜索关键字</p>
</div></div></div></td></tr><tr><td class="sc-cSHVUG sc-chPdSV ffryYJ" kind="field" title="source_origin"><span class="sc-kGXeez bcLONg"></span>source_origin</td><td class="sc-kgoBCf kGwPhO"><div><div><span class="sc-cHGsZl sc-TOsTZ fKyGWc"></span><span class="sc-cHGsZl sc-kgAjT hqYVjx">int</span></div> <div><div class="sc-jWBwVP sc-iRbamj gDsWLk"><p>源码来源，目前支持 <code>1</code>（代码仓库）、<code>2</code>（蓝鲸 LessCode）</p>
</div></div></div></td></tr><tr><td class="sc-cSHVUG sc-chPdSV ffryYJ" kind="field" title="type"><span class="sc-kGXeez bcLONg"></span>type</td><td class="sc-kgoBCf kGwPhO"><div><div><span class="sc-cHGsZl sc-TOsTZ fKyGWc"></span><span class="sc-cHGsZl sc-kgAjT hqYVjx">str</span></div> <div><div class="sc-jWBwVP sc-iRbamj gDsWLk"><p>按应用类型筛选，目前支持：<code>default</code>（默认）、<code>engineless_app</code>（无引擎应用）、<code>bk_plugin</code>（蓝鲸插件）</p>
</div></div></div></td></tr><tr class="last undefined"><td class="sc-cSHVUG sc-chPdSV ffryYJ" kind="field" title="order_by"><span class="sc-kGXeez bcLONg"></span>order_by</td><td class="sc-kgoBCf kGwPhO"><div><div><span class="sc-cHGsZl sc-TOsTZ fKyGWc"></span><span class="sc-cHGsZl sc-kgAjT hqYVjx">string</span></div> <div><div class="sc-jWBwVP sc-iRbamj gDsWLk"><p>排序，可选值：<code>code</code>、<code>created</code>、<code>last_deployed_date</code>、<code>latest_operated_at</code>，默认为升序，前面加 <code>-</code> 后为降序，如 <code>-created</code></p>
</div></div></div></td></tr></tbody></table>

### 返回结果
```json
{
    "count": 2,
    "next": "http://bkpaas.example.com/backend/api/bkapps/applications/lists/detailed?limit=12&amp;offset=12",
    "previous": null,
    "results": [
        {
            "application": {
                "id": "130bd72a-dbf5-419c-8357-9ed914341234",
                "region_name": "内部版",
                "logo_url": "http://example.com/app-logo/blueking_app_default.png",
                "deploy_status": true,
                "deploy_info": {
                    "stag": {
                        "url": "http://apps.example.com/ieod-bkapp-aaaa-stag/",
                        "deployed": true
                    },
                    "prod": {
                        "url": "http://apps.example.com/ieod-bkapp-aaaa-prod/",
                        "deployed": true
                    }
                },
                "region": "ieod",
                "created": "2018-04-25 12:08:54",
                "updated": "2018-06-19 16:54:37",
                "owner": "0236c4ff908f528b",
                "code": "verylongnameaaaa",
                "name": "我就是v3t",
                "language": "Go",
                "source_init_template": "go_gin_hello_world",
                "source_type": "bk_svn",
                "source_repo_id": 432,
                "app_type": "backend",
                "is_active": true,
                "last_deployed_date": null,
                "creator": "0236c4ff908f528b",
                "is_deleted": false
            },
            "product": null,
            "marked": true
        },
        {
            "application": {
                "id": "d403880b-6c46-4edf-b1a0-24363b61234",
                "region_name": "混合云版",
                "logo_url": "http://example.com/app-logo/blueking_app_default.png",
                "deploy_status": true,
                "deploy_info": {
                    "stag": {
                        "url": "http://apps.example.com/clouds-bkapp-appid-stag/",
                        "deployed": true
                    },
                    "prod": {
                        "url": null,
                        "deployed": false
                    }
                },
                "region": "clouds",
                "created": "2018-04-10 16:34:36",
                "updated": "2018-04-10 16:34:36",
                "owner": "0236c4ff908f528b",
                "code": "appid8",
                "name": "测试8",
                "language": "Python",
                "source_init_template": "dj18_hello_world",
                "source_type": "bk_svn",
                "source_repo_id": 425,
                "app_type": "backend",
                "is_active": true,
                "last_deployed_date": null,
                "creator": "0236c4ff908f528b",
                "is_deleted": false
            },
            "product": null,
            "marked": false
        }
	]
}

```

### 返回结果说明
<table class="model"><tbody><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 10784 -->count<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">number</span><div class="markdown"><p>总数</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 10792 -->next<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><div class="markdown"><p>下一页地址</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 10800 -->previous<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><div class="markdown"><p>上一页地址</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 10808 -->results<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class=""><span><span class="model"><span class=""><span class="inner-object"><table class="model"><tbody><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 10826 -->application<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class=""><span class="model-jump-to-path"><!-- react-empty: 10951 --></span><span class="inner-object"><table class="model"><tbody><tr style="color: rgb(102, 102, 102); font-weight: normal;"><td style="font-weight: bold;">description:</td><td><div class="markdown"><p>蓝鲸应用</p>
</div></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 10961 -->id<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 10968 -->example<!-- /react-text --><!-- react-text: 10969 -->: <!-- /react-text --><!-- react-text: 10970 -->87ce9623-39e9-4d10-bfc4-c6827d781fc7<!-- /react-text --></span><div class="markdown"><p>应用 UUID</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 10974 -->region<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 10981 -->example<!-- /react-text --><!-- react-text: 10982 -->: <!-- /react-text --><!-- react-text: 10983 -->ieod<!-- /react-text --></span><div class="markdown"><p>应用区域</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 10987 -->region_name<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 10994 -->example<!-- /react-text --><!-- react-text: 10995 -->: <!-- /react-text --><!-- react-text: 10996 -->腾讯内部版<!-- /react-text --></span><div class="markdown"><p>region对应的中文名称</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11000 -->source_type<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><div class="markdown"><p>应用源码托管类型</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11008 -->source_repo_id<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><div class="markdown"><p>应用源码托管 id</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11016 -->is_active<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">boolean</span><div class="markdown"><p>应用是否活跃</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11024 -->last_deployed_date<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">boolean</span><div class="markdown"><p>应用最近部署时间</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11032 -->code<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><div class="markdown"><p>应用 Code</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11040 -->name<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 11047 -->descrition<!-- /react-text --><!-- react-text: 11048 -->: <!-- /react-text --><!-- react-text: 11049 -->应用名称<!-- /react-text --></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11052 -->logo_url<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 11059 -->descrition<!-- /react-text --><!-- react-text: 11060 -->: <!-- /react-text --><!-- react-text: 11061 -->应用Logo地址<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 11064 -->example<!-- /react-text --><!-- react-text: 11065 -->: <!-- /react-text --><!-- react-text: 11066 -->http://example.com/app-logo/blueking_app_default.png<!-- /react-text --></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11069 -->language<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><div class="markdown"><p>应用使用的编程语言</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11077 -->source_init_template<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><div class="markdown"><p>应用初始化时使用的模板名称</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11085 -->created<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span class="prop-format"><!-- react-text: 11091 -->($<!-- /react-text --><!-- react-text: 11092 -->dateTime<!-- /react-text --><!-- react-text: 11093 -->)<!-- /react-text --></span><div class="markdown"><p>应用创建时间</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11097 -->updated<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span class="prop-format"><!-- react-text: 11103 -->($<!-- /react-text --><!-- react-text: 11104 -->dateTime<!-- /react-text --><!-- react-text: 11105 -->)<!-- /react-text --></span><div class="markdown"><p>应用修改时间</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11109 -->deploy_info<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class=""><span class="inner-object"><table class="model"><tbody><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11166 -->stag<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class=""><span class="inner-object"><table class="model"><tbody><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11198 -->deployed<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">bool</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 11205 -->example<!-- /react-text --><!-- react-text: 11206 -->: <!-- /react-text --><!-- react-text: 11207 -->true<!-- /react-text --></span><div class="markdown"><p>是否部署</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11211 -->url<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 11218 -->example<!-- /react-text --><!-- react-text: 11219 -->: <!-- /react-text --><!-- react-text: 11220 -->http://apps.example.com/stag--appid/<!-- /react-text --></span><div class="markdown"><p>访问链接</p>
</div></span></span></td></tr><tr>&nbsp;</tr></tbody></table></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11179 -->prod<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class=""><span class="inner-object"><table class="model"><tbody><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11230 -->deployed<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">bool</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 11237 -->example<!-- /react-text --><!-- react-text: 11238 -->: <!-- /react-text --><!-- react-text: 11239 -->false<!-- /react-text --></span><div class="markdown"><p>是否部署</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11243 -->url<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 11250 -->example<!-- /react-text --><!-- react-text: 11251 -->: <!-- /react-text --><!-- react-text: 11252 -->http://apps.example.com/appid/<!-- /react-text --></span><div class="markdown"><p>访问链接</p>
</div></span></span></td></tr><tr>&nbsp;</tr></tbody></table></span></span></span></td></tr><tr>&nbsp;</tr></tbody></table></span></span></span></td></tr><tr>&nbsp;</tr></tbody></table></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 10844 -->product<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class=""><span class="inner-object"><table class="model"><tbody><tr style="color: rgb(102, 102, 102); font-weight: normal;"><td style="font-weight: bold;">description:</td><td><div class="markdown"><p>应用市场应用</p>
</div></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11134 -->name<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 11141 -->example<!-- /react-text --><!-- react-text: 11142 -->: <!-- /react-text --><!-- react-text: 11143 -->Awesome App<!-- /react-text --></span><div class="markdown"><p>应用 UUID</p>
</div></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 11147 -->logo<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 11154 -->example<!-- /react-text --><!-- react-text: 11155 -->: <!-- /react-text --><!-- react-text: 11156 -->http://example.com/app-logo/awesome-app.png<!-- /react-text --></span><div class="markdown"><p>应用的logo地址</p>
</div></span></span></td></tr><tr>&nbsp;</tr></tbody></table></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em;"><!-- react-text: 10862 -->marked<!-- /react-text --></td><td style="vertical-align: top;"><span class="model"><span class="prop"><span class="prop-type">boolean</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 10869 -->descripton<!-- /react-text --><!-- react-text: 10870 -->: <!-- /react-text --><!-- react-text: 10871 -->是否关注<!-- /react-text --></span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 10874 -->example<!-- /react-text --><!-- react-text: 10875 -->: <!-- /react-text --><!-- react-text: 10876 -->true<!-- /react-text --></span></span></span></td></tr><tr>&nbsp;</tr></tbody></table></span></span></span></span></span></span></td></tr><tr>&nbsp;</tr></tbody></table>