<template>
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
      <paas-content-loader
        :is-loading="isLoading"
        placeholder="entry-loading"
        :offset-top="20"
        class="app-container middle"
      >
        <section v-show="!isLoading">
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
    <div v-else-if="active === 'user_access_control'">
      <accessUser></accessUser>
    </div>
    <div v-else-if="active === 'ip_access_control'">
      <accessIp></accessIp>
    </div>
    <div v-else-if="active === 'approval'">
      <accessAudit></accessAudit>
    </div>
  </div>
</template>

<script>import visitConfig from './comps/visit-config';
// import domainConfig from './comps/custom-domain';
import accessUser from './comps/access-user';
import accessIp from './comps/access-ip';
import accessAudit from './comps/access-audit';
import portConfig from './comps/port-config';
import appBaseMixin from '@/mixins/app-base-mixin';

export default {
  components: {
    visitConfig,
    // domainConfig,
    accessUser,
    accessIp,
    portConfig,
    accessAudit,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: true,
      active: 'moduleAddress',
    };
  },
  computed: {
    accessControl() {
      return this.$store.state.region.access_control.module.map(e => e);
    },
    panels() {
      console.log('this.accessControl', this.accessControl);
      const panelsData = [{ name: 'moduleAddress', label: this.$t('访问地址') }];
      if (this.accessControl.includes('user_access_control')) {   // 用户限制
        panelsData.push({ name: 'user_access_control', label: this.$t('用户限制') });
      }
      if (this.accessControl.includes('ip_access_control')) {   // IP限制
        panelsData.push({ name: 'ip_access_control', label: this.$t('IP限制') });
      }
      if (this.accessControl.includes('approval')) {   // 单据审批
        panelsData.push({ name: 'approval', label: this.$t('单据审批') });
      }
      return panelsData;
    },
  },
  methods: {
    handlerDataReady() {
      this.isLoading = false;
    },
    goModuleManage() {
      this.$router.push({
        name: 'moduleManage',
        params: {
          id: this.appCode,
          moduleId: this.curModuleId,
        },
      });
    },
    handleTabChange() {
      this.isLoading = true;
    },
  },
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
