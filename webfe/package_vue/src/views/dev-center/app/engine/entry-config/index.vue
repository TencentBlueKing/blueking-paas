<template>
  <div class="right-main">
    <cloud-app-top-bar
      v-if="isCloudNativeApp"
      :title="$t('访问管理')"
      :active="active"
      :nav-list="panels"
      :module-id="curModuleId"
      @change="handleTabChange"
    />
    <div
      v-else
      class="ps-top-bar"
    >
      <h2>
        {{ $t('访问管理') }}
      </h2>
    </div>
    <section :class="['visit-container', { 'cloud-cls': isCustomBackground }]">
      <bk-tab
        v-show="!isCloudNativeApp"
        :active.sync="active"
        ext-cls="domain-tab-cls"
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
        :class="['controller', { default: !isCloudNativeApp }]"
      >
        <paas-content-loader
          :is-loading="isLoading"
          placeholder="entry-loading"
          :offset-top="20"
        >
          <section v-show="!isLoading">
            <visit-config @data-ready="handlerDataReady" />
          </section>
        </paas-content-loader>
      </div>
      <div v-else-if="active === 'user_access_control'">
        <accessUser></accessUser>
      </div>
      <div v-else-if="active === 'process_service_manage'">
        <access-process></access-process>
      </div>
      <div v-else-if="active === 'ip_access_control'">
        <accessIp></accessIp>
      </div>
      <div v-else-if="active === 'approval'">
        <accessAudit></accessAudit>
      </div>
    </section>
  </div>
</template>

<script>
import visitConfig from './comps/visit-config';
import accessUser from './comps/access-user';
import accessIp from './comps/access-ip';
import accessAudit from './comps/access-audit';
import accessProcess from './comps/access-process';
import cloudAppTopBar from '@/components/cloud-app-top-bar.vue';
import appBaseMixin from '@/mixins/app-base-mixin';
import { traceIds } from '@/common/trace-ids';

export default {
  components: {
    visitConfig,
    accessUser,
    accessIp,
    accessAudit,
    accessProcess,
    cloudAppTopBar,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: true,
      active: '',
      initPage: false,
    };
  },
  computed: {
    accessControl() {
      return this.$store.state.region?.access_control
        ? this.$store.state.region?.access_control?.module?.map((e) => e)
        : [];
    },
    panels() {
      let panelsData = [
        { name: 'moduleAddress', label: this.$t('访问地址') },
        { name: 'process_service_manage', label: this.$t('进程服务管理') },
      ];
      // 运营者不需要访问地址
      if (this.curAppInfo.role.name === 'operator') {
        panelsData = [];
      }
      // 开发者只有访问地址
      if (this.curAppInfo.role.name === 'developer') {
        return panelsData;
      }
      if (this.accessControl.includes('user_access_control')) {
        // 用户限制
        panelsData.push({ name: 'user_access_control', label: this.$t('用户限制') });
      }
      if (this.accessControl.includes('ip_access_control')) {
        // IP限制
        panelsData.push({ name: 'ip_access_control', label: this.$t('IP限制') });
      }
      if (this.accessControl.includes('approval')) {
        // 单据审批
        panelsData.push({ name: 'approval', label: this.$t('单据审批') });
      }
      return panelsData;
    },
    isCustomBackground() {
      if (this.isCloudNativeApp) {
        return this.active === 'moduleAddress' || this.active === 'process_service_manage';
      }
      return false;
    },
    categoryText() {
      return this.isCloudNativeApp ? '云原生应用' : '普通应用';
    },
  },
  watch: {
    $route() {
      this.$nextTick(() => {
        if (this.curAppInfo.role.name !== 'operator') {
          this.active = 'moduleAddress';
        } else {
          this.active = 'user_access_control';
        }
      });
    },
  },
  mounted() {
    this.initPage = true;
    this.tab = this.getQueryString('tab');
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
    handleTabChange(v) {
      const label = this.panels.find((item) => item.name === v).label;
      this.sendEventTracking({ id: traceIds[label], action: 'view', category: this.categoryText });
      if (this.initPage) {
        this.active = this.tab || v;
      } else {
        this.active = v;
      }
      const newUrl = `${this.$route.path}?tab=${this.active}`;
      window.history.replaceState('', '', newUrl);
      this.isLoading = true;
      this.initPage = false;
    },

    // 获取地址参数
    getQueryString(name) {
      const reg = new RegExp(`(^|&)${name}=([^&]*)(&|$)`, 'i');
      const r = window.location.search.substr(1).match(reg);
      if (r != null) {
        return decodeURIComponent(r[2]);
      }
      return null;
    },
  },
};
</script>
<style lang="scss" scoped>
.right-main {
  .visit-container {
    background: #fff;
    margin: 24px;
    padding-bottom: 20px;
    &:not(.cloud-cls) {
      box-shadow: 0 2px 4px 0 #1919290d;
      border-radius: 2px;
    }
    &.cloud-cls {
      background: #f5f7fa;
    }
  }
  .domain-tab-cls {
    min-height: auto;
    margin: 0 24px;
    padding-top: 0px !important;
    background: #fff;
    /deep/ .bk-tab-section {
      padding: 0 !important;
    }
  }
  .controller {
    background: #fff;
    min-height: calc(100% - 50px);
    margin: 15px auto 0;
    &.default {
      padding: 0 16px;
    }
    .entry-bar {
      /deep/ .bar-container {
        border: none !important;
      }
    }
  }
  .ps-entry-container {
    background: #fff;
    margin: 16px 24px 0 24px;
    padding: 16px 24px;
  }
}
</style>
