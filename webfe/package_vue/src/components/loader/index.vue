<template lang="html">
    <div :class="[{ 'paas-loading-content': isLoaderShow, 'loading': localLoading, 'fadeout': !localLoading }]" :style="{ 'min-height': localLoading && height ? height + 'px' : 'calc(100% - 50px)' }">
        <div :class="['loading-placeholder', { 'hide': !isLoaderShow }]" :style="{ 'background-color': backgroundColor }">
            <template v-if="placeholder">
                <component
                    :is="placeholder"
                    :style="{ 'padding-top': `${offsetTop}px`, 'margin-left': `${offsetLeft}px`, 'transform-origin': 'left' }"
                    :base-width="baseWidth"
                    :content-width="contentWidth">
                </component>
            </template>
        </div>
        <slot></slot>
    </div>
</template>

<script>
    import ByUserLoading from './loading/by-user'
    import LogLoading from './loading/log'
    import ProcessLoading from './loading/process'
    import IndexLoading from './loading/index'
    import ChartLoading from './loading/chart'
    import AppsLoading from './loading/apps'
    import SummaryLoading from './loading/summary'
    import DeployLoading from './loading/deploy'
    import DeployTopLoading from './loading/deploy-top'
    import DeployInnerLoading from './loading/deploy-inner'
    import EnvLoading from './loading/env'
    import EntryLoading from './loading/entry'
    import DataStoreLoading from './loading/data-store'
    import DataInnerLoading from './loading/data-inner'
    import UserLimitLoading from './loading/user-limit'
    import ModuleManageLoading from './loading/module-manage'
    import OrderLoading from './loading/order'
    import AnalysisLoading from './loading/analysis'
    import MarketLoading from './loading/market'
    import AlarmRecordLoading from './loading/alarm-record'
    import DeployHistoryLoading from './loading/deploy-history'
    import DeployConfigLoading from './loading/deploy-config'
    import DeployInnerHistoryLoading from './loading/deploy-inner-history'
    import BaseInfoLoading from './loading/base-info'
    import RolesLoading from './loading/roles'
    import SearchLoading from './loading/search'
    import CodeLoading from './loading/code'
    import CodeReviewLoading from './loading/code-review'
    import MarketMobileLoading from './loading/market-mobile'
    import MarketInfoLoading from './loading/market-info'
    import MarketVisitLoading from './loading/market-visit'
    import CloudApiLoading from './loading/cloud-api'
    import CloudApiInnerLoading from './loading/cloud-api-inner'
    import MigrationLoading from './loading/migration'
    import DevopsLoading from './loading/devops'
    import ServiceLoading from './loading/service'
    import ServiceInnerLoading from './loading/service-inner'
    import ExemptLoading from './loading/exempt'
    import PackagesLoading from './loading/packages'
    import DocuManagerLoading from './loading/docu-manager'
    import DataInnerSharedLoading from './loading/data-inner-shared'
    import CloudApiInnerIndexLoading from './loading/cloud-api-index-inner'
    import CloudApiIndexLoading from './loading/cloud-api-index'
    import DeployYamlLoading from './loading/deploy-yaml'
    import DeployResourceLoading from './loading/deploy-resource'
    import DeployEnvLoading from './loading/deploy-env'
    import DeployProcessLoading from './loading/deploy-process'
    import DeployHookLoading from './loading/deploy-hook.vue'
    import SummaryPluginLoading from './loading/summary-plugin.vue'
    export default {
        components: {
            ByUserLoading,
            ProcessLoading,
            LogLoading,
            IndexLoading,
            ChartLoading,
            AppsLoading,
            SummaryLoading,
            DeployLoading,
            DeployTopLoading,
            DeployInnerLoading,
            DeployInnerHistoryLoading,
            EnvLoading,
            EntryLoading,
            DataStoreLoading,
            DataInnerLoading,
            UserLimitLoading,
            ModuleManageLoading,
            OrderLoading,
            AnalysisLoading,
            MarketLoading,
            AlarmRecordLoading,
            DeployHistoryLoading,
            DeployConfigLoading,
            BaseInfoLoading,
            RolesLoading,
            SearchLoading,
            CodeLoading,
            CodeReviewLoading,
            MarketMobileLoading,
            CloudApiLoading,
            CloudApiInnerLoading,
            MigrationLoading,
            DevopsLoading,
            ServiceLoading,
            ServiceInnerLoading,
            ExemptLoading,
            MarketInfoLoading,
            MarketVisitLoading,
            PackagesLoading,
            DocuManagerLoading,
            DataInnerSharedLoading,
            CloudApiInnerIndexLoading,
            CloudApiIndexLoading,
            DeployYamlLoading,
            DeployResourceLoading,
            DeployEnvLoading,
            DeployProcessLoading,
            DeployHookLoading,
            SummaryPluginLoading
        },
        props: {
            isLoading: {
                type: Boolean,
                default: false
            },
            placeholder: {
                type: String
            },
            offsetTop: {
                type: [Number, String],
                default: 25
            },
            offsetLeft: {
                type: [Number, String],
                default: 0
            },
            height: {
                type: Number
            },
            delay: {
                type: Number,
                default: 300
            },
            backgroundColor: {
                type: String,
                default: '#FFF'
            }
        },
        data () {
            return {
                localLoading: this.isLoading,
                isLoaderShow: this.isLoading,
                baseWidth: 1180,
                contentWidth: 1180,
                curPlaceholder: ''
            }
        },
        watch: {
            isLoading (newVal, oldVal) {
                // true转false时，让loading动画再运行一段时间，防止过快而闪烁
                if (oldVal && !newVal) {
                    setTimeout(() => {
                        this.localLoading = this.isLoading
                        setTimeout(() => {
                            this.isLoaderShow = this.isLoading
                        }, 200)
                    }, this.delay)
                } else {
                    this.localLoading = this.isLoading
                    this.isLoaderShow = this.isLoading
                }
            }
        },
        mounted () {
            this.initContentWidth()

            window.onresize = () => {
                this.initContentWidth()
            }
        },
        methods: {
            initContentWidth () {
                const winWidth = window.innerWidth
                if (winWidth < 1440) {
                    this.contentWidth = 980
                } else if (winWidth < 1680) {
                    this.contentWidth = 1080
                } else if (winWidth < 1920) {
                    this.contentWidth = 1180
                } else {
                    this.contentWidth = 1280
                }
            }
        }
    }
</script>

<style lang="scss">
  .paas-loading-content {
    position: relative;
    overflow: hidden;

    &.loading {
      * {
        opacity: 0 !important;
      }
    }

    &.fadeout {
      .loading-placeholder {
        opacity: 0 !important;
      }
    }

    .loading-placeholder {
      opacity: 1 !important;
      position: absolute;
      width: 100%;
      height: 100%;
      left: 0;
      right: 0;
      top: 0;
      bottom: 0;
      z-index: 100;
      transition: opacity ease 0.5s;

      &.hide {
        z-index: -1;
      }

      svg {
        width: 1180px;
      }

      * {
        opacity: 1 !important;
      }
    }
  }
  .hide {
    display: none;
  }
</style>
