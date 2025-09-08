<template>
  <CardItem>
    <template #title>
      <div class="flex-row align-items-baseline">
        <span class="card-title mr-8">{{ $t('访问统计') }}</span>
        <bk-button
          text
          title="primary"
          class="p0 f12"
          @click="jumpToAnalysis"
        >
          {{ $t('查看详情') }}
        </bk-button>
      </div>
    </template>
    <template #title-extra>
      <div class="flex-row align-items-center">
        <bk-select
          v-model="activeModule"
          style="width: 116px"
          :clearable="false"
          :disabled="!curAppModuleList?.length"
          behavior="simplicity"
          searchable
          @selected="fetchData"
        >
          <bk-option
            v-for="option in curAppModuleList"
            :key="option.name"
            :id="option.name"
            :name="option.name"
          />
        </bk-select>
        <bk-select
          class="ml10"
          v-model="activeEnv"
          style="width: 116px"
          :clearable="false"
          behavior="simplicity"
          @selected="fetchData"
        >
          <bk-option
            v-for="option in envList"
            :key="option.id"
            :id="option.id"
            :name="option.name"
          />
        </bk-select>
      </div>
    </template>
    <div
      class="flex-row align-self-start mt-12 access-statistics-main"
      v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
    >
      <!-- 访问数据 -->
      <div class="flex-row flex-column left-access-data pr-16">
        <div class="item pv">
          <p class="f24 font-weight-700">{{ metricsData.pv }}</p>
          <p class="f12 g-tip">{{ $t('访问次数 (PV)') }}</p>
        </div>
        <div class="item uv">
          <p class="f24 font-weight-700">{{ metricsData.uv }}</p>
          <p class="f12 g-tip">
            {{ $t('访问次数 (UV)') }}
            <i
              v-bk-tooltips="
                $t(
                  '独立访客数目前是按天统计的，如果选择的时间范围跨天的话，同一个用户会被重复计算，故独立访客数会大于真实的用户数。'
                )
              "
              class="paasng-icon paasng-exclamation-circle"
            />
          </p>
        </div>
      </div>
      <div class="chart-container">
        <chart
          v-if="chartData?.length"
          ref="accessChart"
          :options="chartOptions"
          auto-resize
          style="width: 100%; height: 210px"
        />
        <!-- 无数据 -->
        <bk-exception
          v-else
          class="exception-wrap-item exception-part"
          type="empty"
          scene="part"
        ></bk-exception>
      </div>
    </div>
  </CardItem>
</template>

<script>
import dayjs from 'dayjs';
import { cloneDeep } from 'lodash';
import appBaseMixin from '@/mixins/app-base-mixin';
import CardItem from './card-item.vue';
import ECharts from 'vue-echarts/components/ECharts.vue';
import 'echarts/lib/chart/line';
import 'echarts/lib/component/tooltip';
import 'echarts/lib/component/legend';
import 'echarts/lib/component/grid';
import 'echarts/lib/component/axisPointer';
import defaultChartOptions from '@/json/analysis-chart-option';

export default {
  mixins: [appBaseMixin],
  components: {
    CardItem,
    chart: ECharts,
  },
  inject: ['overviewDateRange'],
  data() {
    return {
      activeModule: '',
      activeEnv: 'stag',
      envList: [
        { id: 'stag', name: this.$t('预发布环境') },
        { id: 'prod', name: this.$t('生产环境') },
      ],
      // 访问量数据
      metricsData: { pv: 0, uv: 0 },
      chartData: [],
      isLoading: false,
    };
  },
  computed: {
    interval() {
      return this.overviewDateRange?.endTime === this.overviewDateRange?.startTime ? '1h' : '1d';
    },
    // ECharts 配置选项
    chartOptions() {
      if (!this.chartData.length) return {};

      // 根据日期范围动态设置 X 轴格式
      const xAxisData = this.getXAxisData();
      const pvData = this.chartData.map((item) => item.pv);
      const uvData = this.chartData.map((item) => item.uv);

      // 使用默认配置
      const options = cloneDeep(defaultChartOptions.pv_uv);

      // 调整 grid 为 legend 预留空间
      options.grid.bottom = '15%';

      // 设置数据
      options.xAxis[0].data = xAxisData;
      options.series = [
        {
          name: 'PV',
          type: 'line',
          data: pvData,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: {
            width: 2,
          },
        },
        {
          name: 'UV',
          type: 'line',
          data: uvData,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: {
            width: 2,
          },
        },
      ];
      // 自定义 legend 样式
      options.legend = {
        data: [
          {
            name: 'PV',
            icon: 'path://M0,1 L8,1 L8,4 L0,4 Z',
          },
          {
            name: 'UV',
            icon: 'path://M0,1 L8,1 L8,4 L0,4 Z',
          },
        ],
        left: 'center',
        bottom: 0,
        orient: 'horizontal',
        itemGap: 20,
        itemWidth: 8,
        itemHeight: 3,
        textStyle: {
          color: '#63656e',
          fontSize: 12,
        },
      };
      return options;
    },
  },
  watch: {
    // 监听日期范围变化
    overviewDateRange: {
      handler(newVal) {
        this.fetchData(newVal);
      },
      deep: true,
    },
    appCode() {
      this.fetchData(this.overviewDateRange);
    },
  },
  created() {
    console.log('created');

    this.activeModule = this.curAppModuleList[0].name || 'default';
  },
  mounted() {
    // 初始化时显示 loading
    this.showChartLoading();
  },
  methods: {
    jumpToAnalysis() {
      this.$router.push({
        name: 'cloudAppWebAnalysis',
        params: { id: this.appCode, moduleId: this.activeModule },
      });
    },
    // 获取图表、uv/pv数据
    fetchData(date) {
      this.isLoading = true;
      this.showChartLoading();
      Promise.all([this.getChartData(date), this.getPvUv(date)]).finally(() => {
        this.isLoading = false;
      });
    },
    // 获取 X 轴数据，根据日期范围动态格式化
    getXAxisData() {
      if (!this.chartData?.length) return [];
      // 根据数据特征判断
      const firstTime = dayjs(this.chartData[0]?.time);
      const lastTime = dayjs(this.chartData[this.chartData.length - 1]?.time);
      const isSameDay = firstTime.isSame(lastTime, 'day');
      if (isSameDay) {
        // 同一天的数据显示小时格式
        return this.chartData.map((item) => dayjs(item.time).format('HH:mm'));
      } else {
        // 跨天数据显示日期格式
        return this.chartData.map((item) => dayjs(item.time).format('MM-DD'));
      }
    },
    // 显示图表加载状态
    showChartLoading() {
      this.$nextTick(() => {
        const chartRef = this.$refs.accessChart;
        if (!chartRef) return;

        chartRef.showLoading({
          text: this.$t('正在加载'),
          color: '#30d878',
          textColor: '#fff',
          maskColor: 'rgba(255, 255, 255, 0.8)',
        });

        requestAnimationFrame(() => {
          chartRef.resize();
        });
      });
    },
    // 隐藏图表加载状态
    hideChartLoading() {
      const chartRef = this.$refs.accessChart;
      chartRef?.hideLoading();
    },
    formatDates({ startTime, endTime }) {
      const start = dayjs(startTime).startOf('day'); // 开始日期的开始时间
      let end;
      // 检查 startTime 和 endTime 是否相同
      if (startTime === endTime) {
        // 若相同，并且日期为今天，使用当前时间
        const today = dayjs().startOf('day');
        if (start.isSame(today)) {
          end = dayjs(); // 当前时间
        } else {
          end = start.endOf('day');
        }
      } else {
        end = dayjs(endTime).endOf('day');
      }
      return {
        formattedStartTime: start.format('YYYY-MM-DD HH:mm:ss'),
        formattedEndTime: end.format('YYYY-MM-DD HH:mm:ss'),
      };
    },
    // 构建请求参数
    buildRequestParams() {
      return {
        appCode: this.appCode,
        moduleId: this.activeModule,
        env: this.activeEnv,
        backendType: 'user_tracker',
        siteName: 'default',
        engineEnabled: true,
      };
    },
    // 获取图表数据
    async getChartData(dateRange) {
      try {
        const { formattedStartTime, formattedEndTime } = this.formatDates(dateRange);
        const params = {
          start_time: formattedStartTime,
          end_time: formattedEndTime,
          interval: this.interval,
        };
        const requestParams = this.buildRequestParams();
        const ret = await this.$store.dispatch('analysis/getChartData', {
          ...requestParams,
          params,
        });
        this.chartData = ret.result.results || [];
      } catch (e) {
        this.chartData = [];
      } finally {
        // 隐藏图表 loading
        setTimeout(() => {
          this.hideChartLoading();
        }, 500);
      }
    },
    // 获取访问量、访客数数据
    async getPvUv(dateRange) {
      try {
        const params = {
          start_time: dateRange.startTime,
          end_time: dateRange.endTime,
          interval: this.interval,
        };
        const requestParams = this.buildRequestParams();
        const res = await this.$store.dispatch('analysis/getPvUv', {
          ...requestParams,
          params,
        });
        this.metricsData = res.result.results || { pv: 0, uv: 0 };
      } catch (err) {
        this.metricsData = { pv: 0, uv: 0 };
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.access-statistics-main {
  .left-access-data {
    flex-shrink: 0;
    width: 164px;
    gap: 3px;
    border-right: 1px solid #f5f7fa;
    .item {
      flex: 1;
      background: #f5f7fa;
      border-radius: 2px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      padding: 10px;
    }
  }

  .chart-container {
    flex: 1;
  }
}
</style>
