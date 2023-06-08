<template lang="html">
  <div class="right-main">
    <bk-tab
      :active.sync="active"
      ext-cls="domain-tab-cls ps-container"
      type="unborder-card"
      @tab-change="handleTabChange"
    >
      <bk-tab-panel
        v-for="(panel, index) in panels"
        :key="index"
        v-bind="panel"
      />
    </bk-tab>
    <div
      v-if="active === 'moduleAddress'"
      class="controller"
    >
      <app-top-bar
        :title="$t('访问入口')"
        :hide-title="true"
        :can-create="canCreateModule"
        :cur-module="curAppModule"
        :module-list="curAppModuleList"
        class="entry-bar"
      />
      <paas-content-loader
        :is-loading="isLoading"
        placeholder="entry-loading"
        :offset-top="20"
        class="app-container middle"
      >
        <section v-show="!isLoading">
          <div
            v-if="curAppModule.is_default"
            class="ps-tip-block is-primary mt15"
          >
            <section class="content">
              <p>
                {{ $t('当前模块是应用主模块，它的访问地址将会作为应用总地址被蓝鲸市场等功能使用') }}
                <a
                  class="fr"
                  href="javascript: void(0);"
                  @click="goModuleManage"
                > {{ $t('修改主模块设置') }} </a>
              </p>
            </section>
          </div>
          <visit-config
            class="mt20 mb35"
            @data-ready="handlerDataReady"
          />
          <port-config
            class="mt20 mb35"
            @data-ready="handlerDataReady"
          />
          <!-- <mobile-config @data-ready="handlerDataReady"></mobile-config> -->
        </section>
      </paas-content-loader>
    </div>
    <div v-else>
      <paas-content-loader
        :is-loading="isLoading"
        placeholder="entry-loading"
        :offset-top="20"
        class="app-container middle ps-entry-container"
      >
        <domain-config
          class="mb35"
          @data-ready="handlerDataReady"
        />
      </paas-content-loader>
    </div>
  </div>
</template>

<script>
    import visitConfig from './comps/visit-config';
    import domainConfig from './comps/custom-domain';
    import portConfig from './comps/port-config';
    import appBaseMixin from '@/mixins/app-base-mixin';
    import appTopBar from '@/components/paas-app-bar';

    export default {
        components: {
            visitConfig,
            domainConfig,
            portConfig,
            appTopBar
        },
        mixins: [appBaseMixin],
        data () {
            return {
                isLoading: true,
                panels: [
                    { name: 'moduleAddress', label: this.$t('模块访问地址') },
                    { name: 'domain', label: this.$t('独立域名') }
                ],
                active: 'moduleAddress'
            };
        },
        methods: {
            handlerDataReady () {
                this.isLoading = false;
            },
            goModuleManage () {
                this.$router.push({
                    name: 'moduleManage',
                    params: {
                        id: this.appCode,
                        moduleId: this.curModuleId
                    }
                });
            },
            handleTabChange () {
                this.isLoading = true;
            }
        }
    };
</script>
<style lang="scss" scoped>
.right-main{
    .domain-tab-cls {
        min-height: auto;
        margin: auto;
        padding-top: 0px !important;
        background: #fff;
        /deep/ .bk-tab-section {
            padding: 0 !important;
        }
    }
    .controller{
      margin: 16px 24px 0 24px;
      background: #fff;
      .entry-bar{
        /deep/ .bar-container{
          border: none !important;
        }
      }
    }
    .ps-entry-container{
      background: #fff;
      margin: 16px 24px 0 24px;
      padding: 16px 24px;
    }
}
</style>
