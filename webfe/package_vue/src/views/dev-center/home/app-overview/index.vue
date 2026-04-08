<template>
  <div>
    <section class="home-top-title">
      <div class="title">
        {{ $t('应用总览') }}
      </div>
      <div class="tools">
        <bk-button
          :theme="'primary'"
          @click="toCreateApp"
        >
          {{ $t('创建应用') }}
        </bk-button>
      </div>
    </section>
    <!-- 开启监控 -->
    <div
      class="app-overview-container"
      v-if="platformFeature.MONITORING"
    >
      <!-- 告警情况 -->
      <div class="alarm-status card-style chart-box">
        <div class="card-title chart-title">
          {{ $t('告警情况') }}
        </div>
        <chart
          style="width: 450px; height: 200px"
          id="alarm-status"
          class="chart-el"
        ></chart>
        <div
          class="default-text"
          v-if="isAlarmLabel"
        >
          <p
            class="vlaue"
            :style="{ color: alarmDefaultLabel.color }"
          >
            {{ alarmDefaultLabel.value }}
          </p>
          <p class="name">{{ alarmDefaultLabel.name }}</p>
        </div>
        <div class="date-change-box">
          <bk-select
            v-model="curDate"
            style="width: 85px"
            :clearable="false"
            ext-cls="date-select-cls"
            @change="handleDateChange"
          >
            <bk-option
              v-for="option in dateList"
              :key="option.id"
              :id="option.id"
              :name="option.label"
            ></bk-option>
          </bk-select>
        </div>
      </div>
      <!-- 应用情况 -->
      <div class="app-status card-style chart-box">
        <div class="card-title chart-title">
          {{ $t('应用情况') }}
          <i
            class="paasng-icon paasng-info-line"
            v-bk-tooltips="{
              content: $t('更新于 {t}之前', { t: appChartInfo.updateTime }),
              theme: 'light',
            }"
          ></i>
        </div>
        <chart
          style="width: 450px; height: 200px"
          id="chart-app-status"
          class="chart-el"
        ></chart>
        <div
          class="default-text"
          v-if="isAppLabel"
        >
          <p
            class="vlaue"
            :style="{ color: appDefaultLabel.color }"
          >
            {{ appDefaultLabel.value }}
          </p>
          <p class="name">{{ appDefaultLabel.name }}</p>
        </div>
      </div>
    </div>
    <!-- 未开启监控：应用类型、应用状态 -->
    <div
      class="app-overview-container"
      v-else
    >
      <!-- 应用类型 -->
      <div class="app-type card-style chart-box">
        <div class="card-title chart-title">
          {{ $t('应用类型') }}
        </div>
        <chart
          style="width: 450px; height: 200px"
          id="chart-app-type"
          class="chart-el"
        ></chart>
        <div
          class="default-text"
          v-if="isAppTypeLabel"
        >
          <p
            class="vlaue"
            :style="{ color: appTypeDefaultLabel.color }"
          >
            {{ appTypeDefaultLabel.value }}
          </p>
          <p class="name">{{ appTypeDefaultLabel.name }}</p>
        </div>
      </div>
      <!-- 应用状态 -->
      <div class="app-deploy-status card-style chart-box">
        <div class="card-title chart-title">
          {{ $t('应用状态') }}
        </div>
        <chart
          style="width: 450px; height: 200px"
          id="chart-app-deploy-status"
          class="chart-el"
        ></chart>
        <div
          class="default-text"
          v-if="isAppDeployStatusLabel"
        >
          <p
            class="vlaue"
            :style="{ color: appDeployStatusDefaultLabel.color }"
          >
            {{ appDeployStatusDefaultLabel.value }}
          </p>
          <p class="name">{{ appDeployStatusDefaultLabel.name }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import alertChartOption from '@/json/home-page-chart-option';
import { formatDate } from '@/common/tools';
import { bus } from '@/common/bus';
import { mapState } from 'vuex';
import ECharts from 'vue-echarts/components/ECharts.vue';
import echarts from 'echarts';

// 图表配置映射表
const CHART_CONFIG = {
  alarm: { id: 'alarm-status', labelKey: 'isAlarmLabel' },
  app: { id: 'chart-app-status', labelKey: 'isAppLabel' },
  appType: { id: 'chart-app-type', labelKey: 'isAppTypeLabel' },
  appDeployStatus: { id: 'chart-app-deploy-status', labelKey: 'isAppDeployStatusLabel' },
};

// 应用类型配置
const APP_TYPE_CONFIG = {
  order: ['default', 'cloud_native', 'engineless_app'],
  colorMap: { cloud_native: '#85CCA8', default: '#3E96C2', engineless_app: '#FFA66B' },
};

// 应用状态配置
const APP_STATUS_CONFIG = {
  order: ['normal', 'not_deployed', 'offline'],
  colorMap: { normal: '#85CCA8', not_deployed: '#FFA66B', offline: '#DCDEE5' },
};

export default {
  name: 'HomeAppOverview',
  components: {
    chart: ECharts,
  },
  data() {
    return {
      chartAppInfo: { total: 0, issueCount: 0 },
      curDate: 1,
      dateList: [
        { label: `1 ${this.$t('天')}`, id: 1 },
        { label: `7 ${this.$t('天')}`, id: 7 },
        { label: `15 ${this.$t('天')}`, id: 15 },
        { label: `1 ${this.$t('个月')}`, id: 30 },
      ],
      curSelectionTime: this.getSpecifiedDate(1),
      // 图表实例
      chartInstances: {},
      // 中心文字显示控制
      isAlarmLabel: true,
      isAppLabel: true,
      isAppTypeLabel: true,
      isAppDeployStatusLabel: true,
    };
  },
  computed: {
    ...mapState(['platformFeature']),
    ...mapState('baseInfo', {
      appChartInfo: 'appChartData',
      alarmChartData: 'alarmChartData',
      statisticsData: 'statisticsData',
    }),
    homeAlarmData() {
      const { count: totalCount, slowQueryCount } = this.alarmChartData;
      if (totalCount === 0) {
        return [{ value: 0, name: this.$t('总告警数'), colorType: 'low', color: '#FFC685' }];
      }
      if (slowQueryCount === 0) {
        return [{ value: totalCount, name: this.$t('总告警数'), colorType: 'low', color: '#FFC685' }];
      }
      return [
        { value: slowQueryCount, name: this.$t('慢查询告警数'), colorType: 'high', color: '#F5876C' },
        { value: totalCount - slowQueryCount, name: this.$t('其他告警数'), colorType: 'low', color: '#FFC685' },
      ];
    },
    homeAlertChartOption() {
      return this.buildChartOption(this.homeAlarmData, { zeroPieColor: '#B5E0AB' });
    },
    alarmDefaultLabel() {
      return this.getDefaultLabel(this.homeAlarmData);
    },

    // ============ 应用情况 ============
    appChartData() {
      const totalAppCount = this.chartAppInfo.total;
      const idleAppCount = this.appChartInfo.idleAppCount;
      const data = [
        { value: idleAppCount, name: this.$t('闲置应用数'), colorType: 'high', color: '#FFA66B' },
        {
          value: totalAppCount - idleAppCount,
          name: totalAppCount === 0 || idleAppCount === 0 ? this.$t('总应用数') : this.$t('活跃应用数'),
          colorType: 'low',
          color: '#3E96C2',
        },
      ];
      return data.find((v) => v.colorType === 'high' && v.value === 0)
        ? data.filter((v) => v.colorType === 'low')
        : data;
    },
    appChartOption() {
      return this.buildChartOption(this.appChartData);
    },
    appDefaultLabel() {
      return this.getDefaultLabel(this.appChartData);
    },

    // ============ 应用类型 ============
    appTypeChartData() {
      const nameMap = {
        cloud_native: this.$t('云原生应用'),
        default: this.$t('普通应用'),
        engineless_app: this.$t('外链应用'),
      };
      return this.buildStatisticsData(this.statisticsData.app_type_counts, APP_TYPE_CONFIG, nameMap, 'type');
    },
    appTypeChartOption() {
      return this.buildChartOption(this.appTypeChartData);
    },
    appTypeDefaultLabel() {
      return this.getDefaultLabel(this.appTypeChartData);
    },

    // ============ 应用状态 ============
    appDeployStatusChartData() {
      const nameMap = {
        not_deployed: this.$t('未部署'),
        normal: this.$t('正常'),
        offline: this.$t('已下架'),
      };
      return this.buildStatisticsData(this.statisticsData.app_status_counts, APP_STATUS_CONFIG, nameMap, 'status');
    },
    appDeployStatusChartOption() {
      return this.buildChartOption(this.appDeployStatusChartData);
    },
    appDeployStatusDefaultLabel() {
      return this.getDefaultLabel(this.appDeployStatusChartData);
    },
  },
  watch: {
    homeAlarmData() {
      this.initChart('alarm');
    },
    appChartData() {
      this.initChart('app');
    },
    appTypeChartData() {
      this.initChart('appType');
    },
    appDeployStatusChartData() {
      this.initChart('appDeployStatus');
    },
  },
  created() {
    this.getAppsInfoCount();
    if (!this.platformFeature.MONITORING) {
      this.getStatistics();
    }
  },
  mounted() {
    const types = this.platformFeature.MONITORING ? ['alarm', 'app'] : ['appType', 'appDeployStatus'];
    types.forEach((type) => this.initChart(type));
  },
  methods: {
    /**
     * 构建统计数据（应用类型/应用状态通用）
     * @param {Array} rawData - 接口原始数据
     * @param {Object} config - 配置 { order, colorMap }
     * @param {Object} nameMap - 名称映射
     * @param {String} keyField - 原始数据中的 key 字段名
     */
    buildStatisticsData(rawData, config, nameMap, keyField) {
      const countsMap = {};
      (rawData || []).forEach((item) => {
        countsMap[item[keyField]] = item.count;
      });
      return config.order.map((key) => {
        const color = config.colorMap[key] || '#DCDEE5';
        return {
          value: countsMap[key] || 0,
          name: nameMap[key] || key,
          colorType: 'low',
          color,
          itemStyle: { color },
        };
      });
    },
    /**
     * 构建图表配置
     */
    buildChartOption(chartData, options) {
      const colors = chartData.map((v) => v.color);
      return alertChartOption(chartData, colors, options);
    },
    /**
     * 获取默认中心标签（第一个 value > 0 的项，否则取第一项）
     */
    getDefaultLabel(chartData) {
      return chartData.find((v) => v.value > 0) ?? (chartData[0] || { value: 0, name: '' });
    },
    /**
     * 初始化/更新图表
     */
    initChart(type) {
      const config = CHART_CONFIG[type];
      if (!config) return;

      // 获取对应的 option（computed 属性名约定）
      const optionMap = {
        alarm: this.homeAlertChartOption,
        app: this.appChartOption,
        appType: this.appTypeChartOption,
        appDeployStatus: this.appDeployStatusChartOption,
      };

      this.$nextTick(() => {
        const el = document.getElementById(config.id);
        if (!el) return;
        const chart = this.chartInstances[type] || echarts.init(el);
        this.chartInstances[type] = chart;
        chart.setOption(optionMap[type]);

        // 控制中心文字显隐
        chart.off('mouseover');
        chart.off('mouseout');
        chart.off('highlight');
        chart.off('downplay');
        chart.on('mouseover', () => {
          this[config.labelKey] = false;
        });
        chart.on('mouseout', () => {
          this[config.labelKey] = true;
        });
        chart.on('highlight', () => {
          this[config.labelKey] = false;
        });
        chart.on('downplay', () => {
          this[config.labelKey] = true;
        });
      });
    },
    async getAppsInfoCount() {
      try {
        const res = await this.$store.dispatch('baseInfo/getAppsInfoCount');
        this.chartAppInfo = res;
        this.chartAppInfo.issueCount = res.issue_type_counts.find((v) => v.issue_type === 'misconfigured')?.count ?? 0;
        this.$store.commit('baseInfo/updateAppChartData', { allCount: this.chartAppInfo.total });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    async getStatistics() {
      try {
        const res = await this.$store.dispatch('baseInfo/getStatistics');
        this.$store.commit('baseInfo/updateStatisticsData', res);
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    toCreateApp() {
      this.$router.push({ name: 'createApp' });
    },
    getSpecifiedDate(daysToSubtract, currentDate = new Date()) {
      if (!(currentDate instanceof Date)) {
        throw new Error('currentDate must be a Date object');
      }
      const resultDate = new Date(currentDate);
      resultDate.setDate(resultDate.getDate() - daysToSubtract);
      return { start: formatDate(resultDate), end: formatDate(currentDate) };
    },
    handleDateChange(day) {
      this.curSelectionTime = this.getSpecifiedDate(day);
      bus.$emit('home-date', this.curSelectionTime);
    },
  },
};
</script>

<style lang="scss" scoped>
.home-top-title {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 12px;
  .title {
    font-weight: 700;
    font-size: 16px;
    color: #313238;
    .tips {
      font-size: 12px;
      font-weight: 400;
      color: #979ba5;
    }
  }
  .tools {
    display: flex;
    .date-select-cls {
      background: #fff;
      margin-right: 12px;
    }
  }
}
.app-overview-container {
  display: flex;
  .mr16 {
    margin-right: 16px;
  }
  .card-style {
    margin-right: 16px;
    &:last-child {
      margin-right: 0;
    }
  }
  .chart-box {
    display: flex;
    justify-content: center;
    .date-change-box {
      position: absolute;
      top: 12px;
      right: 12px;
    }
  }
  .alarm-status,
  .app-status,
  .app-type,
  .app-deploy-status {
    position: relative;
    flex: 1;
    height: 200px;
    background: #fff;
    .chart-title {
      position: absolute;
      top: 12px;
      left: 24px;
    }
    .chart-el {
      height: 100%;
      width: 100%;
    }
    .default-text {
      transition: all 0.3s;
      position: absolute;
      flex-direction: column;
      left: calc(50% - 95px);
      top: calc(50% - 50px);
      height: 100px;
      width: 100px;
      background: transparent;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      .vlaue {
        font-size: 30px;
        font-weight: bold;
        color: #313238;
        line-height: 40px;
        &.high {
          color: #ea3636;
        }
      }
      .name {
        color: #696b73;
        font-size: 12px;
      }
    }
  }
  .ops-dev-score {
    display: flex;
    flex-direction: column;
    width: 200px;
    height: 200px;
    padding: 12px 24px;
    background: #fff;
    .fraction {
      font-weight: 700;
      font-size: 48px;
      color: #313238;
    }
    .info {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      height: 100%;
    }
  }
  .card-title {
    font-weight: 700;
    font-size: 14px;
    color: #63656e;
    i {
      font-size: 14px;
      color: #dcdee5;
    }
  }
}
</style>
