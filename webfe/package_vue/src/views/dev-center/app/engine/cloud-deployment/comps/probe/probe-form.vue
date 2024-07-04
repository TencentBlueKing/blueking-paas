<template>
  <div class="form-wrapper">
    <bk-form
      :label-width="labelWidth"
      :model="formData"
      ext-cls="survival-detection-form"
      ref="probeFormRef"
      :rules="rules"
    >
      <bk-form-item
        :label="$t('探测方法')"
        :required="true"
        :property="'method'"
        :desc="{
          html: methodHtml
        }"
        :error-display-type="'normal'"
      >
        <bk-select
          :disabled="false"
          :clearable="false"
          v-model="curMethod"
          ext-cls="detection-method-cls"
          @change="handleChange"
        >
          <bk-option
            v-for="option in detectionMethodList"
            :key="option.id"
            :id="option.id"
            :name="option.name"
          ></bk-option>
        </bk-select>
      </bk-form-item>
      <template v-if="curMethod === 'http_get'">
        <bk-form-item
          :label="$t('检查端口')"
          :required="true"
          :property="'http_get.port'"
          :error-display-type="'normal'"
        >
          <bk-input
            v-model="formData.http_get.port"
            type="number"
            :allow-number-paste="true"
            :show-controls="false"
            :max="65535"
            :min="1">
          </bk-input>
          <span class="right-tip">1 ~ 65535</span>
        </bk-form-item>
        <bk-form-item
          :label="$t('检查路径')"
          :required="true"
          :property="'http_get.path'"
          :error-display-type="'normal'"
          ext-cls="check-path"
        >
          <bk-input v-model="formData.http_get.path"></bk-input>
        </bk-form-item>
      </template>
      <!-- 就绪 -->
      <bk-form-item
        v-else
        :label="$t('检查端口')"
        :required="true"
        :property="'tcp_socket.port'"
        :error-display-type="'normal'"
      >
        <bk-input
          v-model="formData.tcp_socket.port"
          type="number"
          :show-controls="false"
          :max="65535"
          :min="1">
        </bk-input>
        <span class="right-tip">1 ~ 65535</span>
      </bk-form-item>
      <bk-form-item
        :label="$t('延迟探测时间')"
        :required="true"
        :property="'initial_delay_seconds'"
        :error-display-type="'normal'"
      >
        <bk-input
          v-model="formData.initial_delay_seconds"
          type="number"
          :max="300"
          :min="0"
        >
          <template slot="append">
            <div class="group-text">{{ $t('秒') }}</div>
          </template>
        </bk-input>
        <span class="right-tip">0 ~ 300 {{ $t('秒') }}</span>
      </bk-form-item>
      <bk-form-item
        :label="$t('探测超时时间')"
        :required="true"
        :property="'timeout_seconds'"
        :error-display-type="'normal'"
      >
        <bk-input
          v-model="formData.timeout_seconds"
          type="number"
          :max="60"
          :min="1"
        >
          <template slot="append">
            <div class="group-text">{{ $t('秒') }}</div>
          </template>
        </bk-input>
        <span class="right-tip">1 ~ 60 {{ $t('秒') }}</span>
      </bk-form-item>
      <bk-form-item
        :label="$t('探测频率')"
        :required="true"
        :property="'period_seconds'"
        :error-display-type="'normal'"
      >
        <bk-input
          v-model="formData.period_seconds"
          type="number"
          :max="300"
          :min="2"
        >
          <template slot="append">
            <div class="group-text">{{ $t('秒/次') }}</div>
          </template>
        </bk-input>
        <span class="right-tip">2 ~ 300 {{ $t('秒/次') }}</span>
      </bk-form-item>
      <bk-form-item
        :label="$t('连续探测成功次数')"
        :required="true"
        :property="'success_threshold'"
        :error-display-type="'normal'"
      >
        <bk-input
          v-model="formData.success_threshold"
          type="number"
          :max="3"
          :min="1"
        >
          <template slot="append">
            <div class="group-text">{{ $t('次') }}</div>
          </template>
        </bk-input>
      </bk-form-item>
      <bk-form-item
        :label="$t('连续探测失败次数')"
        :required="true"
        :property="'failure_threshold'"
        :error-display-type="'normal'"
      >
        <bk-input
          v-model="formData.failure_threshold"
          type="number"
          :max="50"
          :min="1"
        >
          <template slot="append">
            <div class="group-text">{{ $t('次') }}</div>
          </template>
        </bk-input>
      </bk-form-item>
    </bk-form>
  </div>
</template>

<script>
import { cloneDeep } from 'lodash';

export default {
  name: 'ProbeForm',
  props: {
    data: {
      type: Object,
      default: () => {},
    },
    probeType: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      curMethod: 'http_get',
      formData: {
        http_get: {
          port: 80,
          path: '/ping',
        },
        tcp_socket: {
          port: 80,
        },
        initial_delay_seconds: 0,
        timeout_seconds: 1,
        period_seconds: 10,
        success_threshold: 1,
        failure_threshold: 3,
      },
      detectionMethodList: [
        { id: 'http_get', name: 'HTTP Get' },
        { id: 'tcp_socket', name: 'TCP Socket' },
      ],
      rules: {
        ['http_get.port']: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
        ],
        ['http_get.path']: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            regex: /^\/.*$/,
            message: this.$t('以 / 开头'),
            trigger: 'blur',
          },
        ],
        ['tcp_socket.port']: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
        ],
        initial_delay_seconds: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
        ],
        timeout_seconds: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
        ],
        period_seconds: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
        ],
        success_threshold: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
        ],
        failure_threshold: [
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
    methodHtml() {
      return `
        <p>${this.$t('成功条件')}：</p>
        <p>HTTP Get：${this.$t('请求状态码为')} 2xx / 3xx</p>
        <p>TCP Socket：${this.$t('指定端口可访问')}</p>
      `;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    labelWidth() {
      return this.localLanguage === 'en' ? 190 : 150;
    },
  },
  watch: {
    data: {
      handler(newVal) {
        const curProbeData = newVal.probes[this.probeType];
        if (curProbeData) {
          // 设置默认值
          this.formData = curProbeData;
          this.init();
        }
      },
      deep: true,
      immediate: true,
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.curMethod = this.formData.http_get ? 'http_get' : 'tcp_socket';
    },
    // 处理表单数据，探测方法， http_get 和 tcp_socket 只能同时有一个
    formattParams() {
      const params = cloneDeep(this.formData);
      if (this.curMethod === 'http_get') {
        params.tcp_socket = null;
      } else {
        params.http_get = null;
      }
      return params;
    },
    handleChange(value) {
      this.setProbeMethodValue(value);
    },
    // 探测表单校验
    async validateFun() {
      await this.$refs.probeFormRef?.validate();
    },
    setProbeMethodValue(type) {
      if (type === 'http_get') {
        this.formData[type] = {
          port: 80,
          path: '/ping',
        };
        this.formData.tcp_socket = null;
      } else {
        this.formData[type] = {
          port: 80,
        };
        this.formData.http_get = null;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.form-wrapper {
  margin: 14px 56px 16px 0;
  padding: 24px 0;
  background: #f5f7fa;
  border-radius: 2px;

  .detection-method-cls.bk-select {
    background: #fff;
  }

  .right-tip {
    position: absolute;
    top: 50%;
    left: 252px;
    transform: translateY(-50%);
    white-space: nowrap;
    color: #63656E;
  }
}
</style>
