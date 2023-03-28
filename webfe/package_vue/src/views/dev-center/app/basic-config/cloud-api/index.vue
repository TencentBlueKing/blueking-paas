<template lang="html">
  <div
    :class="[{ 'plugin-cloud-box': isPlugin }]"
  >
    <div class="ps-top-bar">
      <div class="header-title">
        {{ $t('云API权限管理') }}
        <div class="guide-wrapper">
          <bk-button
            class="f12"
            text
            theme="primary"
            style="margin-right: 10px;"
            @click="toLink('gateway')"
          >
            {{ $t('API 网关接入指引') }}
          </bk-button>
          <bk-button
            class="f12"
            text
            theme="primary"
            style="margin-right: 10px;"
            @click="toLink('API')"
          >
            {{ $t('API 调用指引') }}
          </bk-button>
          <bk-button
            class="f12"
            text
            theme="primary"
            @click="toLink('FAQ')"
          >
            FAQ
          </bk-button>
        </div>
      </div>
    </div>
    <section class="app-container middle">
      <paas-content-loader
        :key="pageKey"
        :is-loading="isLoading"
        placeholder="cloud-api-index-loading"
        :offset-top="12"
        :delay="1000"
      >
        <bk-tab
          :active.sync="active"
          type="unborder-card"
          @tab-change="handleTabChange"
        >
          <bk-tab-panel
            v-for="(panel, index) in panels"
            :key="index"
            v-bind="panel"
          />
        </bk-tab>
        <render-api
          v-if="active === 'gatewayApi'"
          :key="comKey"
          :app-code="appCode"
          @data-ready="handlerDataReady"
        />
        <render-api
          v-if="active === 'componentApi'"
          :key="comKey"
          api-type="component"
          :app-code="appCode"
          @data-ready="handlerDataReady"
        />
        <app-perm
          v-if="active === 'appPerm'"
          @data-ready="handlerDataReady"
        />
        <apply-record
          v-if="active === 'applyRecord'"
          @data-ready="handlerDataReady"
        />
      </paas-content-loader>
    </section>
  </div>
</template>

<script>
    import appBaseMixin from '@/mixins/app-base-mixin';
    import RenderApi from './comps/render-api';
    import AppPerm from './comps/app-perm';
    import ApplyRecord from './comps/apply-record';

    export default {
        components: {
            AppPerm,
            ApplyRecord,
            RenderApi
        },
        mixins: [appBaseMixin],
        data () {
            return {
                isLoading: true,
                linkMap: {
                    'gateway': this.GLOBAL.DOC.APIGW_QUICK_START,
                    'API': this.GLOBAL.DOC.APIGW_USER_API,
                    'FAQ': this.GLOBAL.DOC.APIGW_FAQ
                },
                panels: [
                    { name: 'gatewayApi', label: this.$t('网关API') },
                    { name: 'componentApi', label: this.$t('组件API') },
                    { name: 'appPerm', label: this.$t('已申请的权限') },
                    { name: 'applyRecord', label: this.$t('申请记录') }
                ],
                active: 'gatewayApi',
                comKey: -1,
                pageKey: -1,
                isPlugin: false
            };
        },
        watch: {
            '$route' () {
                this.active = 'gatewayApi';
                this.pageKey = +new Date();
                this.isLoading = true;
            }
        },
        created () {
            this.isPlugin = this.$route.meta && this.$route.meta.isGetAppInfo;
            const tabActive = this.$route.params.tabActive;
            if (tabActive) {
                this.active = tabActive;
            }
        },
        methods: {
            toLink (type) {
                window.open(this.linkMap[type]);
            },

            handlerDataReady () {
                this.isLoading = false;
            },

            handleTabChange () {
                this.comKey = +new Date();
            }
        }
    };

</script>

<style lang="scss" scoped>
    .overview-tit {
        display: flex;
        justify-content: space-between;
        padding: 0 30px;
    }

    .api-type-list {
        padding-top: 16px;
        overflow: hidden;
        border-bottom: solid 1px #e6e9ea;
    }

    .api-type-list a {
        width: 50%;
        height: 34px;
        line-height: 34px;
        text-align: center;
        font-size: 16px;
        color: #5d6075;
        float: left;
        border-bottom: solid 3px #fff;
        cursor: pointer;
    }

    .api-type-list a.active {
        border-bottom: solid 3px #3a84ff;
        color: #3a84ff;
    }

    .plugin-cloud-box {
        .ps-top-bar {
            padding-top: 16px;
            font-size: 16px;
            color: #313238;
            line-height: 24px;
            letter-spacing: 0;
            .header-title {
                border: none;
                margin: 0 50px;
            }
        }
    }
</style>
