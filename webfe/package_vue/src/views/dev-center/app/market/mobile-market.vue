<template>
    <div class="right-main">
        <div class="ps-top-bar">
            <h2> {{ $t('应用市场 (移动端)') }} </h2>
        </div>
        <paas-content-loader class="app-container middle" :is-loading="isDataLoading" placeholder="market-mobile-loading">
            <section class="mobile-config mt25" v-show="!isDataLoading">
                <div class="ps-top-card">
                    <p class="main-title"> {{ $t('蓝鲸企业号') }} </p>
                    <p class="desc">{{ $t('开启移动端配置后允许通过腾讯企业号') }} -> {{GLOBAL.HELPER.name}} {{ $t('访问蓝鲸应用') }}
                        <a :href="GLOBAL.DOC.APP_ENTRY_INTRO" target="blank"> {{ $t('详细使用说明') }} </a>
                    </p>
                </div>

                <div class="content" v-if="mobileConfig.canReleaseToMobile">
                    <div class="controller">
                        <div class="switch-wrapper ps-card" v-for="key of ['stag', 'prod']" :key="key">
                            <div class="header">
                                <span class="title">{{key === 'stag' ? $t('预发布环境') : $t('生产环境')}}</span>
                                <div class="action" @click.stop.prevent="handleShowDialog(key)">
                                    <bk-switcher
                                        v-model="mobileConfig[key].is_enabled">
                                    </bk-switcher>
                                </div>
                            </div>
                            <div class="content" style="height: 195px;">
                                <template v-if="mobileConfig[key].is_enabled">
                                    <div class="url">
                                        {{ $t('移动端访问地址：') }} <span class="text" v-bk-tooltips="mobileConfig[key].access_domain || '--'">{{mobileConfig[key].access_domain || '--'}}</span>
                                        <i class="paasng-icon paasng-edit2 edit" v-bk-tooltips="$t('编辑')" @click="handleEdit(key, mobileConfig[key].access_domain)"></i>
                                    </div>
                                    <div>
                                        <wx-qiye-qrcode
                                            class="vm"
                                            style="border: 1px solid #F0F1F5; border-radius: 2px;"
                                            :url="mobileConfig[key].access_domain"
                                            :size="96">
                                        </wx-qiye-qrcode>
                                        <div class="guide vm mt5">
                                            <div class="path">
                                                <strong>{{ $t('微信请访问') }}:</strong>
                                                <p>
                                                    <span> {{ $t('微信') }} </span>
                                                    <i class="paasng-icon paasng-angle-right"></i>
                                                    <span> {{ $t('通讯录') }} </span>
                                                    <i class="paasng-icon paasng-angle-right"></i>
                                                    <span> {{ $t('腾讯企业号') }} </span>
                                                    <i class="paasng-icon paasng-angle-right"></i>
                                                    <span>{{key === 'stag' ? `${GLOBAL.HELPER.name}测试` : `${GLOBAL.HELPER.name}`}}</span>
                                                </p>
                                            </div>
                                            <div class="path">
                                                <strong>{{ $t('企业微信请访问') }}:</strong>
                                                <p>
                                                    <span> {{ $t('企业微信') }} </span>
                                                    <i class="paasng-icon paasng-angle-right"></i>
                                                    <span> {{ $t('工作台') }} </span>
                                                    <i class="paasng-icon paasng-angle-right"></i>
                                                    <span> {{ $t('更多') }} </span>
                                                    <i class="paasng-icon paasng-angle-right"></i>
                                                    <span>{{key === 'stag' ? `${GLOBAL.HELPER.name}测试` : `${GLOBAL.HELPER.name}`}}</span>
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                </template>
                                <template v-else>
                                    <div class="ps-guide-box mt50">
                                        {{ $t('如需在微信 / 企业微信进行访问') }} <br> {{ $t('请先开启') }} {{key === 'stag' ? $t('预发布环境') : $t('生产环境')}}
                                    </div>
                                </template>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="content" v-else>
                    <p class="description">
                        {{ $t('该功能暂未开放，如需体验请联系') }}
                        <a :href="GLOBAL.HELPER.href" v-if="GLOBAL.HELPER.href">{{GLOBAL.HELPER.name}}</a>
                        <span v-else> {{ $t('管理员') }} </span>
                    </p>
                </div>
            </section>
            <bk-dialog
                width="540"
                v-model="dialogConfig.visiable"
                :title="dialogConfig.title"
                :theme="'primary'"
                :mask-close="false"
                :header-position="'left'"
                :close-icon="!dialogConfig.isLoading"
                :loading="dialogConfig.isLoading"
                @after-leave="handleReset">
                <bk-form ref="form" :label-width="200" form-type="vertical" :model="dialogConfig" :rules="rules">
                    <bk-form-item :label="$t('移动端访问地址：')" :required="true" :property="'url'">
                        <bk-input v-model="dialogConfig.url" :placeholder="`${$t('如')}：http://appid.${GLOBAL.WOA_DOMAIN}.com/mobile/`"></bk-input>
                    </bk-form-item>
                </bk-form>
                <bk-alert class="mt10" :title="$t('只支持 woa 域名，请先在微信、企业微信上验证地址是否访问正常')"></bk-alert>
                <template slot="footer">
                    <bk-button theme="primary" class="mr5" @click="handleConfirm" :loading="dialogConfig.isLoading"> {{ $t('确定') }} </bk-button>
                    <bk-button theme="default" @click="handleCancel" :disabled="dialogConfig.isLoading"> {{ $t('取消') }} </bk-button>
                </template>
            </bk-dialog>

            <bk-dialog
                width="540"
                v-model="disableDialogConfig.visiable"
                v-if="disableDialogConfig.enableConfirm"
                :title="disableDialogConfig.title"
                :theme="'primary'"
                :header-position="'left'"
                :mask-close="false"
                :close-icon="!disableDialogConfig.isLoading"
                :loading="disableDialogConfig.isLoading">
                <p class="mb5"> {{ $t('请完整输入') }} <code>{{appCode}}</code> {{ $t('来确认停用移动端配置！') }} </p>
                <bk-input v-model="disableDialogConfig.appCode" :placeholder="$t('请输入应用 ID')"></bk-input>

                <div class="bk-alert mt10 bk-alert-error">
                    <i class="bk-icon icon-info"></i>
                    <div class="bk-alert-content">
                        <div class="bk-alert-title"> {{ $t('停用后，需要按照') }}《 <a target="_blank" :href="GLOBAL.DOC.APP_ENTRY_INTRO"> {{ $t('指引') }} </a> 》{{ $t('申请移动网关才能重新开启移动端配置') }} </div>
                        <div class="bk-alert-description"></div>
                    </div>
                </div>
                
                <template slot="footer">
                    <bk-button
                        theme="primary"
                        class="mr5"
                        :loading="disableDialogConfig.isLoading"
                        :disabled="disableDialogConfig.appCode !== appCode"
                        @click="disableMobileMarket">
                        {{ $t('确定') }}
                    </bk-button>
                    <bk-button
                        theme="default"
                        :disabled="disableDialogConfig.isLoading"
                        @click="handleCancelDisable">
                        {{ $t('取消') }}
                    </bk-button>
                </template>
            </bk-dialog>

            <bk-dialog
                width="450"
                v-else
                v-model="disableDialogConfig.visiable"
                :title="disableDialogConfig.title"
                :theme="'primary'"
                :header-position="'left'"
                :mask-close="false"
                :close-icon="!disableDialogConfig.isLoading"
                :loading="disableDialogConfig.isLoading">
                <p class="tl" v-if="disableDialogConfig.env === 'stag'"> {{ $t('停用后，在') }} {{GLOBAL.HELPER.name}} {{ $t('测试企业号中将不能访问该应用') }} </p>
                <p class="tl" v-else> {{ $t('停用后，在') }} {{GLOBAL.HELPER.name}} {{ $t('企业号中将不能访问该应用') }} </p>
                <template slot="footer">
                    <bk-button
                        theme="primary"
                        class="mr5"
                        :loading="disableDialogConfig.isLoading"
                        :disabled="disableDialogConfig.enableConfirm && (disableDialogConfig.appCode !== appCode)"
                        @click="disableMobileMarket">
                        {{ $t('确定') }}
                    </bk-button>
                    <bk-button
                        theme="default"
                        :disabled="disableDialogConfig.isLoading"
                        @click="handleCancelDisable">
                        {{ $t('取消') }}
                    </bk-button>
                </template>
            </bk-dialog>
        </paas-content-loader>
    </div>
</template>

<script>
    import appBaseMixin from '@/mixins/app-base-mixin.js';
    import wxQiyeQrcode from '@/components/ui/Qrcode';

    export default {
        components: {
            wxQiyeQrcode
        },
        mixins: [appBaseMixin],
        data () {
            return {
                isDataLoading: false,
                dialogConfig: {
                    visiable: false,
                    title: '',
                    isLoading: false,
                    url: ''
                },
                disableDialogConfig: {
                    visiable: false,
                    title: '',
                    isLoading: false,
                    appCode: ''
                },
                mobileConfig: {
                    stag: {
                        is_enabled: false,
                        access_domain: ''
                    },
                    prod: {
                        is_enabled: false,
                        access_domain: ''
                    },
                    canReleaseToMobile: false,
                    errMsg: `${this.$t('请联系')}${this.GLOBAL.HELPER.name}${this.$t('开启权限!')}`
                },
                rules: {
                    url: [
                        {
                            required: true,
                            message: this.$t('必填项'),
                            trigger: 'blur'
                        },
                        {
                            validator: function (val) {
                                return (val.startsWith('http://') || val.startsWith('https://')) && val.indexOf(`.${window.GLOBAL_CONFIG.WOA_DOMAIN}`) > -1;
                            },
                            message: `${this.$t('只支持 woa 域名，如')}：http://appid.${this.GLOBAL.WOA_DOMAIN}${this.$t('/mobile/')}`,
                            trigger: 'blur'
                        }
                    ]
                }
            };
        },
        watch: {
            '$route' () {
                this.init();
            }
        },
        mounted () {
            this.init();
        },
        methods: {
            init () {
                this.loadMobileConfig();
            },
            async loadMobileConfig () {
                this.isDataLoading = true;
                try {
                    const res = await this.$store.dispatch('market/getMobileMarketInfo', {
                        appCode: this.appCode
                    });
                    this.mobileConfig = Object.assign(this.mobileConfig, res, { canReleaseToMobile: true });
                } catch (err) {
                    this.$paasMessage({
                        theme: 'error',
                        message: err.detail
                    });
                    this.mobileConfig.canReleaseToMobile = false;
                } finally {
                    this.isDataLoading = false;
                    this.$emit('data-ready', 'mobile-config');
                }
            },
            handleShowDialog (env) {
                const isEnabled = this.mobileConfig[env].is_enabled;

                if (isEnabled) {
                    this.disableDialogConfig.env = env;
                    this.disableDialogConfig.title = `${this.$t('是否停用【')}${env === 'stag' ? this.$t('预发布环境') : this.$t('正式环境')}】${this.$t('移动端配置')}`;
                    // 判断下 access_url 为空的话：弹出一个二次确认框；不为空的话，弹出一个普通的二次确认框
                    this.disableDialogConfig.enableConfirm = !this.mobileConfig[env].access_url;
                    this.disableDialogConfig.visiable = true;
                } else {
                    this.dialogConfig.env = env;
                    this.dialogConfig.title = `${this.$t('是否开启【')}${env === 'stag' ? this.$t('预发布环境') : this.$t('正式环境')}】${this.$t('移动端配置')}`;
                    this.dialogConfig.visiable = true;
                }
            },
            handleReset () {
                this.dialogConfig.url = '';
                this.dialogConfig.isLoading = false;
                this.$refs.form.clearError();
            },
            handleConfirm () {
                this.$refs.form.validate().then(() => {
                    this.enableMobileMarket();
                });
            },
            handleEdit (env = 'stag', url = '') {
                this.dialogConfig.env = env;
                this.dialogConfig.url = url;
                this.dialogConfig.title = `【${env === 'stag' ? this.$t('预发布环境') : this.$t('正式环境')}】${this.$t('移动端配置')}`;
                this.dialogConfig.visiable = true;
            },
            handleCancel () {
                this.dialogConfig.visiable = false;
            },
            async enableMobileMarket () {
                if (!this.mobileConfig.canReleaseToMobile) {
                    this.$paasMessage({
                        theme: 'error',
                        message: this.mobileConfig.errMsg
                    });
                    return false;
                }

                if (this.dialogConfig.isLoading) {
                    return false;
                }

                this.dialogConfig.isLoading = true;
                try {
                    const env = this.dialogConfig.env;
                    const res = await this.$store.dispatch('market/enableMobileMarket', {
                        appCode: this.appCode,
                        env: env,
                        data: {
                            access_domain: this.dialogConfig.url
                        }
                    });
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('开启成功')
                    });
                    this.dialogConfig.visiable = false;
                    this.mobileConfig[env] = res;
                } catch (err) {
                    this.$paasMessage({
                        theme: 'error',
                        message: err.detail
                    });
                } finally {
                    this.dialogConfig.isLoading = false;
                }
            },
            handleCancelDisable () {
                this.disableDialogConfig.visiable = false;
                this.disableDialogConfig.enableConfirm = false;
            },
            async disableMobileMarket () {
                if (!this.mobileConfig.canReleaseToMobile) {
                    this.$paasMessage({
                        theme: 'error',
                        message: this.mobileConfig.errMsg
                    });
                    return false;
                }

                if (this.disableDialogConfig.isLoading) {
                    return false;
                }

                this.disableDialogConfig.isLoading = true;
                try {
                    const env = this.disableDialogConfig.env;
                    await this.$store.dispatch('market/disableMobileMarket', {
                        appCode: this.appCode,
                        env: env
                    });
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('停用成功')
                    });
                    this.mobileConfig[env] = {
                        is_enabled: false,
                        access_domain: ''
                    };
                    this.disableDialogConfig.visiable = false;
                    this.disableDialogConfig.enableConfirm = false;
                } catch (err) {
                    this.$paasMessage({
                        theme: 'error',
                        message: err.detail
                    });
                } finally {
                    this.disableDialogConfig.isLoading = false;
                }
            }
        }
    };
</script>

<style lang="scss" scoped>
    .mobile-config {
        > .content {
            display: flex;

            .description {
                font-size: 13px;
                padding: 15px 0;
                width: 35%;
            }

            .controller {
                width: 100%;
                display: flex;
                padding: 20px 0px 0px 0;
                justify-content: space-between;

                .switch-wrapper {
                    width: 48.6%;

                    .content {
                    }
                    .guide {
                        display: inline-block;
                        margin-left: 20px;

                        strong {
                            font-size: 12px;
                            font-weight: bold;
                            color: #63656E;
                            margin-bottom: 10px;
                            display: inline-block;
                        }
                    }
                    .path {
                        padding: 5px 0px 10px 0;
                        font-size: 12px;
                        color: #52525d;
                        line-height: 1;

                        .paasng-icon {
                            font-size: 12px;
                            vertical-align: middle;
                        }

                        span {
                            color: #3A84FF;
                            vertical-align: middle;
                        }
                    }
                }
            }
        }

        .wx-qrcode {
            width: 87px;
            height: 87px;
        }
    }
    .action {
        position: relative;
        &::after {
            content: '';
            position: relative;
            position: absolute;
            left: 0;
            right: 0;
            top: 0;
            bottom: 0;
            margin: auto;
            z-index: 10;
            cursor: pointer;
        }
    }
    .url {
        position: relative;
        font-size: 14px;
        padding: 0 0 15px 0;
        margin-bottom: 15px;
        border-bottom: 1px solid #eee;

        .text {
            max-width: 280px;
            display: inline-block;
            text-overflow: ellipsis;
            overflow: hidden;
            white-space: nowrap;
            vertical-align: middle;
        }

        .edit {
            position: absolute;
            right: 0;
            cursor: pointer;
            top: 10px;
        }
    }
</style>
