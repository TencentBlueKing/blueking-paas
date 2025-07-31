<template>
  <div class="metric-container">
    <div :class="['label-title', { en: localLanguage === 'en' }]">
      <span>{{ `Metric ${$t('采集')}` }}</span>
    </div>
    <div class="metric-content">
      <div class="title">
        <!-- 进程服务管理，Metric也直接关闭，并且为禁用状态 -->
        <bk-switcher
          v-model="metric"
          theme="primary"
          @change="handlerChange"
        ></bk-switcher>
        <span class="metric-tips">
          <i class="paasng-icon paasng-info-line"></i>
          <span
            v-dompurify-html="metricTipsHtml"
          ></span>
        </span>
      </div>
      <!-- 编辑模式 -->
      <div class="form-container" v-if="metric">
        <bk-form
          :label-width="145"
          :model="metricData"
          :rules="rules"
          ref="metricForm"
          ext-cls="metric-form-cls"
        >
          <!-- 根据端口映射获取 -->
          <bk-form-item
            :label="$t('端口名称')"
            :required="true"
            :property="'service_name'"
            :error-display-type="'normal'"
          >
            <bk-select
              :disabled="false"
              v-model="metricData.service_name"
              ext-cls="service-select-custom"
              @change="handleChangeName">
              <bk-option
                v-for="option in data.services"
                :key="option.name"
                :id="option.name"
                :name="option.name">
              </bk-option>
            </bk-select>
          </bk-form-item>
          <bk-form-item
            :label="`Metric ${$t('路径')}`"
            :required="true"
            :property="'path'"
            :error-display-type="'normal'"
          >
            <bk-input v-model="metricData.path" @input="handleChangePath"></bk-input>
          </bk-form-item>
          <bk-form-item
            :label="`Metric ${$t('参数')}`"
          >
            <key-value-form
              ref="keyValueForm"
              :data="metricData.params"
              @update="handleUpdateParams"
            />
          </bk-form-item>
        </bk-form>
      </div>
    </div>
  </div>
</template>

<script>
import keyValueForm from './key-value-form.vue';
import { cloneDeep } from 'lodash';

const defaultMetricData = {
  service_name: '',
  path: '',
  params: {},
};

export default {
  name: 'Metric',
  components: {
    keyValueForm,
  },
  props: {
    data: {
      type: Object,
      default: (() => {}),
    },
    isEdit: {
      type: Boolean,
      default: false,
    },
    dashboardUrl: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      metric: false,
      metricData: {
        service_name: '',
        path: '',
        params: {},
      },
      // 端口列表
      serviceNameList: [],
      rules: {
        service_name: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
        ],
        path: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    metricTipsHtml() {
      const monitoringDashboard = `<a href="${this.dashboardUrl}" target="_blank">${this.$t('蓝鲸监控仪表盘')}</a>`;
      return this.$t('配置 Metric 采集后，您可以在 {s} 功能中进行配置并查看您的仪表盘。', { s: monitoringDashboard });
    },
    appCode() {
      return this.$route.params.id;
    },
  },
  watch: {
    'data.services'(newVal) {
      if (!newVal.length) {
        this.metric = false;
      }
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      const curMetric = this.data.monitoring?.metric ?? {};
      this.metric = !!Object.keys(curMetric).length;
      this.metricData = cloneDeep(this.metric ? curMetric : defaultMetricData);
    },
    async metricValidate() {
      await this.$refs.metricForm?.validate();
      // 后续校验
      // await this.$refs.keyValueForm?.validateFun();
    },
    // 启停Metric
    handlerChange(flag) {
      // 关闭 进程服务，同时关闭 Metric
      // 开启 Metric，同时开启 进程服务
      this.$emit('toggle-metric', flag ? cloneDeep(defaultMetricData) : null);
      if (flag) {
        if (!this.metricData || !Object.keys(this.metricData).length) {
          this.metricData = {
            service_name: '',
            path: '',
            params: {},
          };
        }
        if (!this.serviceNameList.length) {
          // 开启进程服务
          this.$emit('enable-service', true);
        }
      }
    },
    handleChangeName(name) {
      this.$emit('updated-data', {
        name: this.data.name,
        key: 'service_name',
        value: name,
      });
    },
    handleChangePath(path) {
      this.$emit('updated-data', {
        name: this.data.name,
        key: 'path',
        value: path,
      });
    },
    handleUpdateParams(data) {
      this.$emit('updated-data', {
        name: this.data.name,
        key: 'params',
        value: data,
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.metric-container {
  display: flex;
  margin: 22px 0;
  .metric-tips {
    color: #63656E;
    font-size: 12px;
    margin-left: 16px;
    i {
      font-size: 14px;
      color: #979BA5;
      transform: translateY(0px);
    }
    span {
      margin-left: 3px;
    }
  }
  .metric-guide-cls {
    padding: 0;
  }
  .view-model {
    .tag {
      display: inline-block;
      height: 22px;
      line-height: 22px;
      padding: 0 8px;
      font-size: 12px;
      color: #63656E;
      background: #F0F1F5;
      border-radius: 2px;
      &.enable {
        color: #14A568;
        background: #E4FAF0;
      }
    }
  }
  .label-title {
    width: 150px;
    line-height: 32px;
    text-align: right;
    vertical-align: middle;
    font-size: 14px;
    font-weight: 400;
    color: #63656e;
    padding-right: 24px;
    white-space: nowrap;
    flex-shrink: 0;
    &.en {
      width: 190px;
    }
  }
  .metric-content {
    flex: 1;
    .title {
      display: flex;
      align-items: center;
      font-size: 12px;
      margin-bottom: 6px;
      line-height: 32px;
      color: #63656e;
    }
  }
  .form-container {
    margin-right: 56px;
    background: #f5f7fa;
    border-radius: 2px;
    padding: 24px 0;
    .metric-form-cls {
      width: 560px;
      .key-value-item {
        display: flex;
        .bk-form-item {
          margin-top: 0 !important;
        }
      }
    }
    .service-select-custom {
      background: #fff;
    }
  }
}
</style>
