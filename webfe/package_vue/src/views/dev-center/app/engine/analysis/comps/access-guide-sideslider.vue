<template>
    <bk-sideslider
        :is-show.sync="isShowSideslider"
        quick-close
        :width="630"
        ext-cls="paas-analysis-sideslider-cls"
        @animation-end="handleAnimationEnd">
        <div slot="header">
            {{ $t('接入指引') }}
            <span class="info" v-if="title !== ''">({{ title }})</span>
        </div>
        <div slot="content" style="padding: 15px 30px;">
            <p class="tips"> {{ $t('如需接入统计，请在页面尾部的') }} &lt;/body&gt; {{ $t('标签前，增加以下代码：') }} </p>
            <p class="tips warn"> {{ $t('注意：所有使用蓝鲸 Python(Django) 框架的应用默认已嵌入该脚本，无需重复添加。') }} </p>
            <template v-if="!engineEnable">
                <div class="script-content">
                    <i class="paasng-icon paasng-general-copy copy-icon" v-copy="copyText"></i>
                    <div class="examples">
                        &lt;!-- BK Analytics 把以下代码放在最后 --&gt;<br>
                        &lt;script src=&quot;{{GLOBAL.LINK.STATIC_JS_API}}&quot; charset=&quot;utf-8&quot;&gt;&lt;/script&gt;<br>
                        &lt;script&gt;<br>
                        &nbsp;&nbsp;&nbsp;&nbsp;// siteName 是网站的唯一标识，请不要修改<br>
                        &nbsp;&nbsp;&nbsp;&nbsp;BKANALYSIS.init({siteName:&nbsp;'{{siteName}}'})<br>
                        &lt;/script&gt; <br>
                        &lt;!-- End BK Analytics --&gt;<br>
                    </div>
                </div>
            </template>
            <template v-else>
                <div class="script-content">
                    <i class="paasng-icon paasng-general-copy copy-icon" v-copy="copyText"></i>
                    <div class="examples">
                        &lt;!-- BK Analytics {{ $t('把以下代码放在最后') }} --&gt;<br>
                        &lt;script src=&quot;{{GLOBAL.LINK.STATIC_JS_API}}&quot; charset=&quot;utf-8&quot;&gt;&lt;/script&gt;<br>
                        &lt;script&gt;<br>
                        &nbsp;&nbsp;&nbsp;&nbsp;BKANALYSIS.init()<br>
                        &lt;/script&gt; <br>
                        &lt;!-- End BK Analytics --&gt;<br>
                    </div>
                </div>
                <p class="tips mb10">{{ $t('该地址仅供 **内部版** 应用使用，其他版本暂不支持该功能。') }}</p>

                <template v-if="!isEvent">
                    <strong class="tips"> {{ $t('其他注意事项：') }} </strong>
                    <p class="tips"> {{ $t('只有通过以下地址访问，才能保证数据被正确统计：') }} </p>
                    <p class="tips">- {{ $t('蓝鲸PaaS平台 v3 版本分配的独立域名，如：') }}http(s)://go-app-template.{{curAppInfo.cluster.ingress_config.app_root_domain}}/</p>
                    <p class="tips">- {{ $t('蓝鲸PaaS平台分配的子路径访问地址，如：') }}http(s)://{{curAppInfo.cluster.ingress_config.sub_path_domain}}/ieod-bkapp-ds-tools-stag/</p>
                    <p class="tips mb10">- {{ $t('在蓝鲸PaaS平台上注册过的独立域名') }}</p>
                </template>
            </template>

            <template v-if="isEvent">
                <strong class="tips pt20"> {{ $t('接入自定义事件统计：') }} </strong>
                <p class="tips"> {{ $t('这里以一个站点需要统计用户使用搜索功能频率为例') }} </p>
                <p class="tips">- {{ $t('首先需要引入上述提供的js脚本并初始化') }}</p>
                <p class="tips">- {{ $t('然后在相应的元素使用') }}<code>bk-trace</code> {{ $t('属性配置参数来进行埋点，具体参数如下') }} </p>
                <div class="examples">
                    &lt;bk-button theme="primary" :title="$t('submit')" bk-trace="{id: 'UserSearchButton', action: 'click', category: 'UserManage'}"&gt;$t('search')&lt;/bk-button&gt;
                </div>
                <p class="tips">- {{ $t('js脚本会在初初化后对页面的带有') }}<code>bk-trace</code> {{ $t('属性元素进行监听并自动上报定义的参数') }} </p>
                <p class="tips">- {{ $t('也可以通过') }} <code>sendEvent</code> {{ $t('API主动上报你的自定义事件数据，具体代码如下：') }} </p>
                <div class="examples">
                    BKANALYSIS.sendEvent({category: 'UserManage', id: 'UserSearchButton' , action: 'click' })
                </div>
                <p class="tips"> {{ $t('更多请参考：') }} <a :href="GLOBAL.DOC.PA_ANALYSIS_CUSTOM" target="_blank"> {{ $t('如何接入自定义事件统计') }} </a></p>
            </template>
            <template v-else>
                <p class="tips mb10"> {{ $t('更多请参考：') }} <a :href="GLOBAL.DOC.PA_ANALYSIS_WEB" target="_blank"> {{ $t('如何接入网站访问统计') }} </a></p>
            </template>
        </div>
    </bk-sideslider>
</template>
<script>
    import appBaseMixin from '@/mixins/app-base-mixin';

    export default {
        name: '',
        mixins: [appBaseMixin],
        props: {
            isShow: {
                type: Boolean,
                default: false
            },
            title: {
                type: String,
                default: ''
            },
            siteName: {
                type: String,
                default: ''
            },
            engineEnable: {
                type: Boolean,
                default: true
            },
            isEvent: {
                type: Boolean,
                default: false
            }
        },
        data () {
            return {
                isShowSideslider: false,
                copyText: ''
            };
        },
        computed: {
            entranceConfig () {
                return this.$store.state.region.entrance_config;
            }
        },
        watch: {
            isShow (value) {
                this.isShowSideslider = !!value;
                if (this.isShowSideslider) {
                    this.$nextTick(() => {
                        const targetDom = document.getElementsByClassName('examples')[0];
                        this.copyText = targetDom.innerText;
                    });
                }
            }
        },
        methods: {
            handleAnimationEnd () {
                this.isShowSideslider = false;
                this.$emit('update:isShow', false);
            }
        }
    };
</script>
<style lang="scss" scoped>
    .paas-analysis-sideslider-cls {
        .info {
            color: #979ba5;
            font-size: 12px;
            font-weight: normal;
        }
        .tips {
            line-height: 24px;
            font-size: 13px;
        }
        .bold {
            font-weight: 700;
        }
        .warn {
            color: #ff9c01;
        }
        .script-content {
            position: relative;
            .copy-icon {
                position: absolute;
                top: 8px;
                right: 8px;
                cursor: pointer;
                font-size: 16px;
                &:hover {
                    color: #3a84ff;
                }
            }
        }
        .examples {
            margin: 10px 0;
            padding: 15px;
            line-height: 18px;
            background: #f5f6fa;
            font-size: 12px;
            background: #f5f6fa;
            border: 1px solid #dcdee5;
            border-radius: 2px;
        }
    }
</style>
