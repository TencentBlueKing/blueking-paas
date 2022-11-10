<template lang="html">
    <div v-if="baseInfo">
        <h3>{{ baseInfo.envName }}</h3>
        <dl>
            <dd>
                <div v-if="appDeployInfo.hasDeployed">
                    <p>
                        <i class="paasng-icon paasng-branch-line text-success middle-list-icon"></i>{{appDeployInfo.branch}}
                    </p>
                    <p>
                        <i class="paasng-icon paasng-dynamic-line text-primary middle-list-icon"></i>
                        {{ $t('由') }}<span class="gruy">{{appDeployInfo.username}}</span>{{ $t('于') }} {{smartTime(appDeployInfo.time,'smartShorten')}} {{appDeployInfo.isEnvOfflined ? $t('下架') : $t('部署')}}
                    </p>
                    <!-- <p v-if="baseInfo.canPublishToMarket && curAppModule.is_default"> -->
                    <p v-if="curAppModule.is_default && environment === 'prod'">
                        <i class="paasng-icon paasng-market-line text-warn middle-list-icon" style="top: 8px;font-size: 16px;"></i>
                        {{baseInfo.marketPublished ? $t('已发布到应用市场') : $t('未发布到应用市场')}}
                        <router-link :to="{ name: 'appMarket', params: { id: appCode } }" class="blue text-padding-default">[{{ $t('管理') }}]</router-link>
                    </p>
                    <div class="panel-controls">
                        <a :href="appDeployInfo.url" class="bk-button bk-button-normal bk-success mr5" target="_blank" v-if="!appDeployInfo.isEnvOfflined"> {{ $t('访问') }} </a>
                        <a class="bk-button bk-button-normal bk-success is-disabled mr5" v-else> {{ $t('访问') }} </a>
                        <router-link class="bk-button bk-button-normal bk-primary is-outline" :to="baseInfo.appUrl">
                            {{ $t('部署') }}
                        </router-link>
                    </div>
                </div>
                
                <div class="grayPanel noDeploy" v-if="!appDeployInfo.hasDeployed">
                    <p><i class="paasng-icon paasng-branch-line text-default middle-list-icon"></i> {{ $t('暂未部署') }} </p>
                    <div class="panel-controls">
                        <bk-button :disabled="true" class="mr5"> {{ $t('访问') }} </bk-button>
                        <router-link class="bk-button bk-button-normal bk-primary is-outline" :to="baseInfo.appUrl">
                            {{ $t('部署') }}
                        </router-link>
                    </div>
                </div>
            </dd>
            <dd v-if="appDeployInfo.hasDeployed">
                <p v-for="(pro, index) in appDeployInfo.proc" :key="index">
                    {{pro.name}}
                    <span :class="[{ 'green': pro.status === $t('正在运行') },{ 'danger': pro.status !== $t('正在运行') }]">→</span>
                    {{pro.status}}
                </p>
            </dd>
        </dl>
    </div>
</template>

<script>
    export default {
        props: {
            appCode: {
                type: String
            },
            environment: {
                type: String
            },
            appDeployInfo: {
                type: Object
            }
        },
        data () {
            return {
                baseInfo: null
                // canPublishToMarket: false
            };
        },
        computed: {
            curAppInfo () {
                return this.$store.state.curAppInfo;
            },
            curAppModule () {
                return this.$store.state.curAppModule;
            }
        },
        created () {
            this.init();
        },
        methods: {
            async init () {
                // const webConfig = this.curAppInfo.web_config
                const configInfo = this.curAppInfo.application.config_info;

                if (this.environment === 'prod') {
                    this.baseInfo = {
                        envName: this.$t('生产环境'),
                        appUrl: {
                            name: 'appDeployForProd',
                            params: {
                                id: this.appCode
                            },
                            query: {
                                focus: 'prod'
                            }
                        },
                        marketPublished: configInfo.market_published
                        // canPublishToMarket: webConfig.can_publish_to_market
                    };
                } else {
                    this.baseInfo = {
                        envName: this.$t('预发布环境'),
                        appUrl: {
                            name: 'appDeploy',
                            params: {
                                id: this.appCode
                            }
                        },
                        marketPublished: false
                        // canPublishToMarket: false
                    };
                }
            }
        }
    };
</script>
<style lang="scss" scoped>
    .noDeploy {
        &.grayPanel {
            p {
                color: #ccc;
            }
        }
    }

    div.panel-controls {
        margin-top: 16px;
    }

    div.panel-controls a.ps-btn {
        margin-right: 8px;
        padding: 8px 26px;
    }

    .environment {
        width: 879px;
        float: left;
        overflow: hidden;
    }

    .environment-box {
        padding-top: 30px;
        color: #666;
    }

    .environment-box h3 {
        line-height: 36px;
    }

    .environment-box dd {
        padding: 7px 0 7px 0;
    }

    .environment-box dd.first {
        width: 360px;
    }

    .environment-box dd.second {
        width: 475px;
    }

    .environment-box dd p {
        padding-left: 25px;
        position: relative;
        color: #666;
    }

    .environment-box .environment-dl {
        border: solid 1px #e6e9ea;
        border-radius: 2px;
        margin-left: 0;
        padding: 0 20px;
    }

    .environment-box dl:after {
        top: 0;
        left: 380px;
        height: 100%;
        margin-left: 0;
        background: #e6e9ea;
    }

    .middle-list li {
        width: 100%;
        line-height: 32px;
        color: #666;
        overflow: hidden;
        border-bottom: solid 1px #e6e9ea;
        padding-bottom: 24px;
    }

    .middle-list li.lilast {
        border-bottom: none;
    }

    .middle-list li p {
        padding-left: 25px;
        position: relative;
    }

    .middle-list-icon {
        position: absolute;
        left: 2px;
        top: 10px;
        font-weight: bold;
    }

    .middle-list dl {
        overflow: hidden;
        position: relative;
    }

    .middle-list dd {
        width: 50%;
        float: left;
        line-height: 32px;
    }

    .middle-list dt {
        line-height: 32px;
    }

    .middle-list dl:after {
        content: "";
        position: absolute;
        left: 50%;
        top: 10px;
        width: 1px;
        height: 100px;
        background: #e9edee;
    }

    .middle-list .green {
        color: #5bd18b;
        padding: 0 6px;
    }

    .middle-list .danger {
        color: #ff7979;
        padding: 0 6px;
    }

    .bk-button {
        width: 80px;
    }
</style>
