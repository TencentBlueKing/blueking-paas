<template lang="html">
    <div class="container biz-create-success">
        <div class="ps-top-bar">
            <div class="header-title">
                <span class="app-code">{{ curAppCode }}</span>
                <i class="paasng-icon paasng-angle-down arrows"></i>
                {{ $t('访问入口') }}
            </div>
        </div>
        <paas-content-loader :is-loading="isLoading" placeholder="entry-loading" class="app-container middle">
            <div class="app-container middle ps-main">
                <!-- 访问入口暂时不展示 -->
                <div class="ps-top-card">
                    <p class="main-title"> {{ $t('访问入口') }} </p>
                    <p class="desc">
                        {{ $t('平台给应用分配的默认访问地址') }}
                    </p>
                    <table class="ps-table ps-table-border mt20" style="width: 100%;">
                        <!-- 通过 type 判断是子域名还是子路径（1. 子路径 2. 子域名） -->
                        <!-- 通过 is_running 判断域名是否可以访问，可访问前端样式为 href，不可访问时为普通文本 -->
                        <tr v-for="(item, key) of moduleEntryInfo.entrancesTemplate" :key="key">
                            <td class="has-right-border td-title">{{key === 'prod' ? $t('生产') : $t('预发布')}}{{ $t('环境') }} </td>
                            <td>
                                <div v-for="e in item" :key="e.address" class="pt10 pb10">
                                    <span>{{e.address || '--'}}</span>
                                    <a :href="e.address" target="_blank" class="card-edit ml5 f12" v-if="e.is_running">
                                        {{ $t('点击访问') }}
                                    </a>
                                </div>
                            </td>
                        </tr>
                    </table>
                </div>
                <div class="ps-top-card config-wrapper">
                    <Domain @closeLoading="changeLoading"></Domain>
                </div>
            </div>
        </paas-content-loader>
    </div>
</template>

<script>
    import appBaseMixin from '@/mixins/app-base-mixin';
    import Domain from './domain.vue';

    export default {
        components: { Domain },
        mixins: [appBaseMixin],
        data () {
            return {
                moduleEntryInfo: {
                    entrances: [],
                    type: 1,
                    entrancesTemplate: {}
                },
                isLoading: true,
                domainConfigList: [],
                tableLoading: false
            };
        },
        created () {
            this.init();
        },
        methods: {
            init () {
                this.getEntryInfo();
            },

            async getEntryInfo () {
                try {
                    const res = await this.$store.dispatch('entryConfig/getEntryInfo', {
                        appCode: this.appCode,
                        moduleId: this.curModuleId
                    });
                    this.moduleEntryInfo = res;
                    this.moduleEntryInfo.entrancesTemplate = res.entrances.reduce((p, v) => {
                        p[v.env].push(v);
                        return p;
                    }, { 'stag': [], 'prod': [] });
                } catch (e) {
                    this.moduleEntryInfo = {
                        entrances: [],
                        type: 1,
                        entrancesTemplate: {}
                    };
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 500);
                }
            },

            changeLoading () {
                this.isLoading = false;
            }
        }
    };
</script>

<style lang="scss" scoped>

    .ps-main {
        margin-top: 15px;
    }
    .header-title {
        display: flex;
        align-items: center;
        .app-code {
            color: #979BA5;
        }
        .arrows {
            margin: 0 9px;
            transform: rotate(-90deg);
            font-size: 12px;
            font-weight: 600;
            color: #979ba5;
        }
    }

    .config-wrapper {
        margin-top: 45px;
    }
</style>
