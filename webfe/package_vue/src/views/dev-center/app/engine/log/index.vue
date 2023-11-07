<template lang="html">
  <div
    :key="appCode"
    class="right-main"
  >
    <app-top-bar
      v-if="!isCloudNativeApp"
      :title="$t('日志查询')"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
    />

    <cloud-app-top-bar
      v-else
      :title="$t('日志查询')"
      :module-id="curModuleId"
      :app-code="appCode"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
    />

    <paas-content-loader
      class="app-container log-middle"
      :class="{ 'log-container': tabActive === 'stream' }"
      :is-loading="isLoading"
      placeholder="log-loading"
      :offset-top="60"
    >
      <section>
        <bk-tab
          :active.sync="tabActive"
          type="unborder-card"
          @tab-change="handleTabChange"
        >
          <template slot="setting">
            <a
              class="f12 pr20"
              :href="GLOBAL.DOC.LOG_QUERY_USER"
              target="_blank"
            >
              {{ $t('如何查询应用日志') }}
            </a>
          </template>
          <bk-tab-panel
            v-if="isStructuredLogTab"
            name="structured"
            :label="$t('结构化日志')"
          >
            <custom-log
              v-if="tabActive === 'structured'"
              ref="customLog"
            />
          </bk-tab-panel>
          <bk-tab-panel
            name="stream"
            :label="$t('标准输出日志')"
          >
            <standart-log v-if="tabActive === 'stream'" />
          </bk-tab-panel>
          <bk-tab-panel
            name="access"
            :label="$t('访问日志')"
          >
            <access-log
              v-if="tabActive === 'access'"
              ref="accessLog"
            />
          </bk-tab-panel>
        </bk-tab>
      </section>
    </paas-content-loader>
  </div>
</template>

<script>import appBaseMixin from '@/mixins/app-base-mixin';
import appTopBar from '@/components/paas-app-bar';
import customLog from './custom-log.vue';
import standartLog from './standart-log.vue';
import accessLog from './access-log.vue';
import cloudAppTopBar from '@/components/cloud-app-top-bar.vue';

export default {
  components: {
    appTopBar,
    customLog,
    standartLog,
    accessLog,
    cloudAppTopBar,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      name: 'log-component',
      tabActive: '',
      tabChangeIndex: 0,
      isLoading: true,
    };
  },
  computed: {
    curAppInfo() {
      return this.$store.state.curAppInfo;
    },
    enableBkLogCollector() {
      return this.curAppInfo.feature?.ENABLE_BK_LOG_COLLECTOR;
    },
    // eslint-disable-next-line vue/return-in-computed-property
    isStructuredLogTab() {
      if (this.curAppInfo.application.type !== 'cloud_native') {
        return true;
      }
      return this.enableBkLogCollector;
    },
  },
  watch: {
    tabActive() {
      this.$nextTick(() => {
        if (this.tabActive === 'structured') {
          this.$refs.customLog?.initTableBox();
        }
        if (this.tabActive === 'access') {
          this.$refs.accessLog.initTableBox();
        }
      });
    },
  },
  mounted() {
    this.isLoading = true;
    this.tabActive = this.isStructuredLogTab ? 'structured' : 'stream';
    // 存在query参数的情况
    const tabActiveName = this.$route.query.tab;
    if (tabActiveName) {
      const tabNameList = ['stream', 'access'];
      if (this.isStructuredLogTab) {
        tabNameList.push('structured');
      }
      this.tabActive = tabNameList.includes(tabActiveName) ? tabActiveName : 'stream';
    }
    setTimeout(() => {
      this.isLoading = false;
    }, 2000);
  },
  methods: {
    handleTabChange(payload) {
      this.$router.push({
        name: 'appLog',
        params: {
          id: this.$route.params.id,
          moduleId: this.$route.params.moduleId,
        },
        query: {
          tab: payload,
        },
      });
    },
  },
};
</script>

<style scoped lang="scss">
.log-middle {
  background: #fff;
  padding-top: 0px;
  margin: 16px auto 30px;
  width: calc(100% - 48px);
  .log-container {
    margin-bottom: 0;
  }
}
</style>
