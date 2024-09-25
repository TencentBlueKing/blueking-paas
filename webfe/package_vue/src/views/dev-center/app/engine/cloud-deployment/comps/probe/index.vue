<template>
  <div :class="['probe-container', { 'view': !isEdit }]">
    <!-- 编辑态 -->
    <div class="probe-options" v-if="isEdit">
      <div :class="['label-title', { en: localLanguage === 'en' }]">
        <span>{{ $t('健康探测') }}</span>
      </div>
      <bk-checkbox-group
        v-model="probeList"
        @change="handlerChange"
      >
        <div class="probe-wrapper">
          <div class="title-wrapper">
            <bk-checkbox value="liveness">
              {{ $t('存活探测') }}
              <span @click.stop>
                <i class="paasng-icon paasng-info-line"></i>
                {{ $t('探测容器是否正常，不正常则会重启容器，在容器生命周期中，该探针会按照设定频率持续运行') }}
              </span>
            </bk-checkbox>
          </div>
          <!-- 存活探测 - 编辑态 -->
          <probe-form
            v-if="enableSurvivalDetection"
            ref="livenessRef"
            :data="processData"
            :probe-type="'liveness'"
          />
        </div>
        <div class="probe-wrapper">
          <div class="title-wrapper">
            <bk-checkbox value="readiness">
              {{ $t('就绪探测') }}
              <span @click.stop>
                <i class="paasng-icon paasng-info-line"></i>
                {{ $t('探测容器是否就绪，若未就绪则不会转发流量到该实例，在容器就绪之前该探针会按照设定频率持续运行') }}
              </span>
            </bk-checkbox>
          </div>
          <!-- 就绪探测 - 编辑态 -->
          <probe-form
            v-if="enableReadinessDetection"
            ref="readinessRef"
            :data="processData"
            :probe-type="'readiness'"
          />
        </div>
      </bk-checkbox-group>
    </div>

    <div class="probe-options" v-else>
      <div :class="['label-title', { en: localLanguage === 'en' }]">
        <span>{{ $t('健康探测') }}：</span>
      </div>
      <div class="view-content">
        <template v-if="probeList.length">
          <!-- 存活探测 -->
          <probe-view
            class="mr24"
            :title="$t('存活探测')"
            :data="processData"
            :probe-type="'liveness'"
          />
          <!-- 就绪探测 -->
          <probe-view
            :title="$t('就绪探测')"
            :data="processData"
            :probe-type="'readiness'"
          />
        </template>
        <span v-else class="probe-tag">
          {{ $t('未启用') }}
        </span>
      </div>
    </div>
  </div>
</template>

<script>
import probeForm from './probe-form.vue';
import ProbeView from './probe-view.vue';

const LIVENESS = 'liveness';
const READINESS = 'readiness';

export default {
  name: 'Probe',
  components: {
    probeForm,
    ProbeView,
  },
  props: {
    processData: {
      type: Object,
      default: () => {},
    },
    isEdit: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      // liveness、readiness、startup
      probeList: [],
    };
  },
  computed: {
    // 存活探测
    enableSurvivalDetection() {
      return this.probeList.includes(LIVENESS);
    },
    // 就绪探测
    enableReadinessDetection() {
      return this.probeList.includes(READINESS);
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  watch: {
    processData(newVal) {
      this.init(newVal);
    },
  },
  created() {
    this.init(this.processData);
  },
  methods: {
    init(data) {
      this.probeList = Object.entries(data?.probes || {})
        .filter(([key, value]) => value !== null)
        .map(([key, value]) => key);
    },
    // 探测启停
    handlerChange() {
      this.handlerProbeChange();
    },
    // 探针校验
    async probeValidate() {
      await this.$refs.livenessRef?.validateFun();
      await this.$refs.readinessRef?.validateFun();
    },
    handlerProbeChange() {
      if (this.probeList.includes(LIVENESS)) {
        this.setProbeData('livenessRef', LIVENESS);
      } else {
        this.setDefault(LIVENESS);
      }
      if (this.probeList.includes(READINESS)) {
        this.setProbeData('readinessRef', READINESS);
      } else {
        this.setDefault(READINESS);
      }
    },
    // 设置探测数据
    setProbeData(refName, type) {
      this.$nextTick(() => {
        const data = this.$refs[refName].formattParams();
        this.$emit('change-form-data', {
          name: this.processData.name,
          key: type,
          data,
        });
      });
    },
    // 停用探测默认值
    setDefault(type) {
      this.$emit('change-form-data', {
        name: this.processData.name,
        key: type,
        data: null,
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.probe-container {
  margin-top: 24px;
  &.view {
    margin-bottom: 24px;
  }
  .probe-options {
    display: flex;
  }
  :deep(.probe-wrapper) {
    margin-bottom: 10px;
    &:last-child {
      margin-bottom: 26px;
    }
    .title-wrapper {
      line-height: 22px;
      .bk-form-checkbox {
        display: flex;
        .bk-checkbox {
          flex-shrink: 0;
        }
      }
      .bk-checkbox-text span {
        margin-left: 15px;
        font-size: 12px;
        color: #63656E;
        i {
          font-size: 14px;
          transform: translateX(-4px);
          color: #979BA5;
        }
      }
    }
  }
  .label-title {
    width: 150px;
    text-align: right;
    vertical-align: middle;
    line-height: 22px;
    font-size: 14px;
    font-weight: 400;
    color: #63656e;
    padding: 0 24px 0 0;
    white-space: nowrap;
    flex-shrink: 0;
    &.en {
      width: 190px;
    }
  }
  :deep(.survival-detection-form) {
    width: 625px;
    .bk-form-item:not(.check-path) {
      .bk-form-content {
        width: 240px;
      }
    }
    .right-tip {
      font-size: 12px;
      color: #63656e;
    }
  }
  .view-content {
    display: flex;

    .mr24 {
      margin-right: 24px;
    }
    .probe-tag {
      display: inline-block;
      height: 22px;
      padding: 0 8px;
      font-size: 12px;
      line-height: 22px;
      color: #63656E;
      background: #F0F1F5;
      border-radius: 2px;
    }
  }
}
</style>
