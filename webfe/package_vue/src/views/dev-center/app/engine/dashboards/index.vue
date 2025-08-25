<template>
  <div class="right-main dashboards-container">
    <top-bar
      ref="topBar"
      :key="appCode"
      :title="$t('仪表盘')"
      :data="dashboardList"
      :loading="isSelectLoading"
      @change="handleChange"
      @redirect="handleRedirect"
    />
    <paas-content-loader
      class="app-container dashboards-content"
      :is-loading="isLoading"
      placeholder="dashboard-loading"
      :offset-top="60"
    >
      <!-- 暂无仪表盘功能 -->
      <FunctionalDependency
        v-if="!isMonitoringEnabled"
        mode="page"
        :title="$t('暂无仪表盘功能')"
        :functional-desc="
          $t(
            '仪表盘功能为您提供了一个直观的视图，帮助您实时监控和分析应用的性能和健康状态。通过可自定义的图表和指标，您可以轻松查看关键数据，如响应时间、错误率、资源使用情况等。'
          )
        "
        :guide-title="$t('如需使用该功能，需要部署「蓝鲸监控：监控日志套餐」')"
        @gotoMore="gotoMore"
      />
      <!-- 暂无部署应用 -->
      <template v-else>
        <section v-if="!dashboardList.length">
          <bk-exception
            class="exception-wrap-item dashboards-exception-part"
            type="empty"
            scene="part"
          >
            <p class="title">{{ $t('暂无仪表盘') }}</p>
            <p class="tips">{{ $t('应用部署成功后，才会内置仪表盘') }}</p>
            <bk-button
              :theme="'primary'"
              @click="toDeploy"
            >
              {{ $t('去部署') }}
            </bk-button>
          </bk-exception>
        </section>
        <!-- 仪表盘 -->
        <template v-else>
          <bk-alert
            type="info"
            class="alert-cls"
            :show-icon="false"
          >
            <div slot="title">
              {{
                $t(
                  '平台内置了开发框架仪表盘，应用需开启 Metric 配置并在代码中上报 Metric 数据后，才可在仪表盘中查看相关数据'
                )
              }}
              <bk-button
                ext-cls="guidelines-cls"
                text
                size="small"
                @click="gotoMore"
              >
                {{ $t('Metric 上报指引') }}
                <i class="paasng-icon paasng-jump-link"></i>
              </bk-button>
            </div>
          </bk-alert>
          <iframe
            id="iframe-embed"
            :src="displayDashboardData.dashboard_url"
            scrolling="no"
            frameborder="0"
          />
        </template>
      </template>
    </paas-content-loader>
  </div>
</template>

<script>
import topBar from './comps/top-bar.vue';
import appBaseMixin from '@/mixins/app-base-mixin';
import FunctionalDependency from '@blueking/functional-dependency/vue2/index.umd.min.js';
export default {
  name: 'CloudDashboards',
  components: {
    topBar,
    FunctionalDependency,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      dashboardList: [],
      displayDashboardData: {},
      isLoading: true,
      dashboardLink: '',
      isSelectLoading: false,
    };
  },
  computed: {
    isMonitoringEnabled() {
      return this.$store.state.platformFeature.MONITORING;
    },
  },
  watch: {
    $route() {
      this.init();
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      Promise.all([this.getBuiltinDashboards(), this.getAppDashboardInfo()]).finally(() => {
        setTimeout(() => {
          this.isLoading = false;
        }, 500);
      });
    },
    // 获取仪表盘数据
    async getBuiltinDashboards() {
      this.isSelectLoading = true;
      try {
        const res = await this.$store.dispatch('getBuiltinDashboards', {
          appCode: this.appCode,
        });
        this.dashboardList = res;
        if (this.dashboardList.length) {
          this.displayDashboardData = this.dashboardList[0];
        }
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isSelectLoading = false;
      }
    },
    // 获取仪表盘链接
    async getAppDashboardInfo() {
      try {
        const res = await this.$store.dispatch('baseInfo/getAppDashboardInfo', {
          appCode: this.appCode,
        });
        this.dashboardLink = res.dashboard_url || '';
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    handleChange(data) {
      this.displayDashboardData = data;
    },
    handleRedirect() {
      window.open(this.dashboardLink, '_blank');
    },
    gotoMore() {
      window.open(this.GLOBAL.DOC.MONITORING_METRICS_GUIDE, '_blank');
    },
    // 部署
    toDeploy() {
      this.$router.push({
        name: 'cloudAppDeployManageStag',
        params: {
          id: this.appCode,
          moduleId: this.curModuleId,
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.dashboards-container {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  .guidelines-cls {
    height: auto;
    line-height: unset;
  }
  .dashboards-content {
    flex: 1;
    display: flex;
    flex-direction: column;
  }
  .alert-cls {
    flex-shrink: 0;
    margin-bottom: 16px;
  }
  iframe#iframe-embed {
    flex: 1;
    width: 100%;
    height: 100%;
    /* resize seems to inherit in at least Firefox */
    -webkit-resize: none;
    -moz-resize: none;
    resize: none;
  }
  .dashboards-exception-part {
    /deep/ .part-img img {
      height: 200px;
    }
    .title {
      font-size: 24px;
      color: #4d4f56;
      line-height: 32px;
      margin-bottom: 16px;
    }
    .tips {
      font-size: 14px;
      color: #979ba5;
      line-height: 22px;
      margin-bottom: 24px;
    }
  }
}
</style>
