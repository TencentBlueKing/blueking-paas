<template lang="html">
    <div class="right-main">
        <paas-content-loader :is-loading="isLoading" :placeholder="loaderPlaceholder" :offset-top="30" class="app-container middle overview">
            <div class="title">{{$t('应用编排')}}</div>
            <section class="deploy-panel deploy-main mt15">
                <ul class="ps-tab" style="position: relative; z-index: 10;">
                    <li :class="['item', { 'active': deployModule === 'process' }]" @click="handleGoPage('cloudAppDeployForProcess')">
                        {{ $t('进程配置') }}
                        <router-link :to="{ name: 'appDeployForStag' }"></router-link>
                    </li>
                    <li :class="['item', { 'active': deployModule === 'hook' }]" @click="handleGoPage('cloudAppDeployForHook')">
                        {{ $t('钩子命令') }}
                    </li>
                    <li :class="['item', { 'active': deployModule === 'env' }]" @click="handleGoPage('cloudAppDeployForEnv')">
                        {{ $t('环境变量') }}
                    </li>
                    <li :class="['item', { 'active': deployModule === 'resource' }]" @click="handleGoPage('cloudAppDeployForResource')">
                        {{ $t('依赖资源') }}
                    </li>
                    <li :class="['item', { 'active': deployModule === 'yaml' }]" @click="handleGoPage('cloudAppDeployForYaml')">
                        {{ $t('YAML') }}
                    </li>
                </ul>

                <div class="deploy-content">
                    <router-view ref="square" :key="renderIndex" :cloudAppData="cloudAppData"></router-view>
                </div>
            </section>

            <div class="deploy-btn-wrapper">
                <bk-dropdown-menu
                    ref="dropdown"
                    align="right"
                    trigger="click"
                    @show="dropdownShow"
                    @hide="dropdownHide">
                    <bk-button
                        :loading="buttonLoading"
                        class="pl20 pr20"
                        :theme="'primary'"
                        slot="dropdown-trigger">
                        {{ $t('发布') }}
                        <i :class="['paasng-icon paasng-down-shape f12',{ 'paasng-up-shape': isDropdownShow }]" style="top: -1px;"></i>
                    </bk-button>
                    <ul class="bk-dropdown-list" slot="dropdown-content">
                        <li><a href="javascript:;" style="margin: 0;" @click="handleDeploy('stag')"> {{ $t('预发布环境') }} </a></li>
                        <li><a href="javascript:;" style="margin: 0;" @click="handleDeploy('prod')"> {{ $t('生产环境') }} </a></li>
                    </ul>
                </bk-dropdown-menu>
            </div>

        </paas-content-loader>
    </div>
</template>

<script>
    import appBaseMixin from '@/mixins/app-base-mixin.js';

    export default {
        components: {
        },
        mixins: [appBaseMixin],
        data () {
            return {
                isLoading: true,
                renderIndex: 0,
                cloudAppData: {},
                isDropdownShow: false,
                isLargeDropdownShow: false,
                buttonLoading: false
            };
        },
        computed: {
            buildpacks () {
                if (this.overview.buildpacks && this.overview.buildpacks.length) {
                    const buildpacks = this.overview.buildpacks.map(item => item.display_name);
                    return buildpacks.join('，');
                }
                return '--';
            },
            deployModule () {
                return this.$route.meta.module || 'stag';
            },
            routeName () {
                return this.$route.name;
            },
            loaderPlaceholder () {
                if (this.routeName === 'appDeployForStag' || this.routeName === 'appDeployForProd') {
                    return 'deploy-loading';
                } else if (this.routeName === 'appDeployForHistory') {
                    return 'deploy-history-loading';
                }
                return 'deploy-top-loading';
            }
        },
        watch: {
            '$route' (newVal, oldVal) {
                if (newVal.params.id !== oldVal.params.id || newVal.params.moduleId !== oldVal.params.moduleId) {
                    this.renderIndex++;
                    this.init();
                }
            }
        },
        created () {
            this.init();
        },
        methods: {

            async init () {
                try {
                    const res = await this.$store.dispatch('deploy/getCloudAppYaml', {
                        appCode: this.appCode
                    });
                    this.cloudAppData = res.manifest;
                    this.$store.commit('cloudApi/updateCloudAppData', this.cloudAppData);
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || e.message
                    });
                } finally {
                    this.isLoading = false;
                }
            },

            handleGoPage (routeName) {
                if (this.$refs.square.envVarList) {
                    const data = this.$store.state.cloudApi.cloudAppData;
                    data.spec.configuration.env = this.$refs.square.envVarList.filter(item => item.name !== '' && item.value !== '');
                    this.$store.commit('cloudApi/updateCloudAppData', data);
                }

                this.cloudAppData = this.$store.state.cloudApi.cloudAppData;
                this.$router.push({
                    name: routeName
                });
            },

            dropdownShow () {
                this.isDropdownShow = true;
            },
            dropdownHide () {
                this.isDropdownShow = false;
            },
            triggerHandler () {
                this.$refs.dropdown.hide();
            },

            async handleDeploy (env) {
                this.$bkInfo({
                    title: `确认发布至${env === 'stag' ? '预发布' : '生产'}环境`,
                    subTitle: `确认要将应用（${this.appCode}）发布到${env === 'stag' ? '预发布' : '生产'}环境`,
                    confirmLoading: true,
                    confirmFn: async () => {
                        // 表单校验, 弹出提示
                        let flag = true;
                        const data = this.$store.state.cloudApi.cloudAppData;
                        const processes = data.spec.processes;
                        const imageReg = /^(?:(?=[^:\/]{1,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?\/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])(?:\/(?![._-])[a-z0-9._-]*(?<![._-]))*)(?::(?![.-])[a-zA-Z0-9_.-]{1,128})?$/;
                        const portReg = /^[0-9]*$/;
                        for (let i = 0; i < processes.length; i++) {
                            // image 镜像地址
                            if (!processes[i].image) {
                                this.$bkMessage({
                                    theme: 'error',
                                    message: this.$t('请输入容器镜像地址!')
                                });
                                flag = false;
                                // 触发验证函数
                                this.$refs.square.formDataValidate(i);
                                break;
                            }
        
                            if (!imageReg.test(processes[i].image)) {
                                this.$bkMessage({
                                    theme: 'error',
                                    message: this.$t('地址格式不正确')
                                });
                                flag = false;
                                this.$refs.square.formDataValidate(i);
                                break;
                            }

                            // 不填 targetPort, 这个 key 需要传
                            if (processes[i].targetPort === '' || processes[i].targetPort === null || processes[i].targetPort === undefined) {
                                delete processes[i].targetPort;
                            } else {
                                if (processes[i].targetPort < 1 || processes[i].targetPort > 65535) {
                                    this.$bkMessage({
                                        theme: 'error',
                                        message: this.$t('端口有效范围1-65535')
                                    });
                                    flag = false;
                                    this.$refs.square.formDataValidate(i);
                                    break;
                                }
                                if (!portReg.test(processes[i].targetPort)) {
                                    this.$bkMessage({
                                        theme: 'error',
                                        message: this.$t('只能输入数字')
                                    });
                                    flag = false;
                                    this.$refs.square.formDataValidate(i);
                                    break;
                                }
                            }
        
                            // replicas 副本数量
                            if (!processes[i].replicas) {
                                this.$bkMessage({
                                    theme: 'error',
                                    message: this.$t('请输入副本数量!')
                                });
                                flag = false;
                                this.$refs.square.formDataValidate(i);
                                break;
                            }
                            if (!(processes[i].replicas >= 0 && processes[i].replicas <= 5)) {
                                this.$bkMessage({
                                    theme: 'error',
                                    message: this.$t('副本数量有效值范围0-5')
                                });
                                flag = false;
                                this.$refs.square.formDataValidate(i);
                                break;
                            }
                        }

                        if (!flag) {
                            return;
                        }

                        // 环境变量
                        const envArr = data.spec.configuration.env;
                        for (let i = 0; i < envArr.length; i++) {
                            if (!envArr[i].name) {
                                this.$bkMessage({
                                    theme: 'error',
                                    message: this.$t('NAME是必填项')
                                });
                                flag = false;
                                this.envProcessor(i);
                                break;
                            }
                            if (!envArr[i].value) {
                                this.$bkMessage({
                                    theme: 'error',
                                    message: this.$t('VALUE是必填项')
                                });
                                flag = false;
                                this.envProcessor(i);
                                break;
                            }
                            if (envArr[i].value.length > 2048) {
                                this.$bkMessage({
                                    theme: 'error',
                                    message: this.$t('VALUE不能超过2048个字符')
                                });
                                flag = false;
                                this.envProcessor(i);
                                break;
                            }
                        }
                       
                        if (!flag) {
                            return;
                        }

                        try {
                            this.buttonLoading = true;
                            await this.$store.dispatch('deploy/sumbitCloudApp', {
                                params: { manifest: this.$store.state.cloudApi.cloudAppData },
                                appCode: this.appCode,
                                moduleId: this.curModuleId,
                                env
                            });
                            this.$paasMessage({
                                theme: 'success',
                                message: '操作成功'
                            });
                            this.$router.push({
                                name: 'appStatus',
                                query: { env }
                            });
                        } catch (e) {
                            this.$paasMessage({
                                theme: 'error',
                                message: e.detail || e.message
                            });
                        } finally {
                            this.buttonLoading = false;
                        }
                    }
                });
            },

            async envProcessor (i) {
                this.handleGoPage('cloudAppDeployForEnv');
                await this.$nextTick();
                this.$refs.square.formDataValidate(i);
            }
        }
    };
</script>

<style lang="scss" scoped>
@import '../../../../../assets/css/components/conf.scss';
@import './index.scss';
    .title{
        font-size: 16px;
        color: #313238;
    }
    .deploy-btn-wrapper {
        // position: absolute;
        // top: 77vh;
        margin-top: 20px;
        width: 1280px;
        background: #E1ECFF;
        height: 50px;
        line-height: 50px;
        padding: 0 20px;
        border-radius: 2px;
    }
@media screen and (max-width: 1920px) {
    .deploy-btn-wrapper {
        width: 1180px;
    }
}

@media screen and (max-width: 1680px) {
    .deploy-btn-wrapper {
        width: 1080px;
    }
}

@media screen and (max-width: 1440px) {
    .deploy-btn-wrapper {
        width: 980px;
    }
}
</style>
