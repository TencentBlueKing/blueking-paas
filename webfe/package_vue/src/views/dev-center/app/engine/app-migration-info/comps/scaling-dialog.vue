<template>
  <bk-dialog
    v-model="processConfigDialog.visible"
    width="576"
    :title="$t('web进程扩缩容')"
    :header-position="'left'"
    :theme="'primary'"
    :mask-close="false"
    @after-leave="handleAfterLeave"
  >
    <template #footer>
      <bk-button
        :theme="'primary'"
        :loading="processConfigDialog.isLoading"
        @click="handleConfirm"
      >
        {{ $t('确定') }}
      </bk-button>
      <bk-button
        :theme="'default'"
        @click="handleCancel"
      >
        {{ $t('取消') }}
      </bk-button>
    </template>
    <div style="min-height: 65px">
      <!-- 处于迁移中的应用，可操作的服务有限 -->
      <bk-radio-group
        v-model="autoscaling"
        class="mb20"
      >
        <bk-radio-button
          class="radio-cls"
          :value="false"
          :disabled="autoscaling"
          v-bk-tooltips="{ content: $t('迁移中的应用不支持切换扩缩容方案'), disabled: !autoscaling }"
        >
          {{ $t('手动调节') }}
        </bk-radio-button>
        <bk-radio-button
          class="radio-cls"
          :value="true"
          :disabled="!autoscaling"
          v-bk-tooltips="{ content: $t('迁移中的应用不支持切换扩缩容方案'), disabled: autoscaling }"
        >
          {{ $t('自动调节') }}
        </bk-radio-button>
      </bk-radio-group>
      <bk-form
        ref="manualAdjustmentForm"
        :label-width="110"
        style="width: 520px"
        :model="processPlan"
      >
        <bk-form-item :label="$t('当前副本数：')">
          <span>{{ curTargetReplicas }}</span>
        </bk-form-item>
        <!-- 自动扩缩容 -->
        <template v-if="autoscaling">
          <bk-form-item :label="$t('触发条件：')">
            <div class="rate-container">
              <span>
                {{ $t('CPU 使用率') }} =
                <bk-input
                  class="w80"
                  v-model="defaultUtilizationRate"
                  disabled
                ></bk-input>
              </span>
              <i
                class="paasng-icon paasng-exclamation-circle uv-tips ml10"
                v-bk-tooltips="autoScalingTip"
              />
            </div>
          </bk-form-item>
          <bk-form-item
            class="desc-form-item"
            :label-width="10"
          >
            <div class="desc-container">
              <p>
                {{ $t('当 CPU 使用率') }} >
                <span class="cpu-num">85%</span>
                {{ $t('时，会触发扩容') }}
              </p>
              <p>
                {{ $t('当 CPU 使用率') }} &lt;
                <span class="cpu-num">{{ shrinkLimit }}</span>
                {{ $t('时，会触发缩容') }}
              </p>
            </div>
          </bk-form-item>
        </template>
        <bk-form-item
          v-else
          :label="$t('副本数量：')"
          :required="true"
          :rules="processPlanRules.targetReplicas"
          :property="'targetReplicas'"
          class="manual-form-cls"
          error-display-type="normal"
        >
          <!-- 普通扩缩容的 -->
          <bk-input
            v-model="processPlan.targetReplicas"
            type="number"
            class="dia-input"
            :min="0"
          />
        </bk-form-item>
      </bk-form>
      <div
        class="auto-container"
        v-if="autoscaling"
      >
        <!-- 自动扩缩容 -->
        <bk-form
          :model="scalingConfig"
          ref="scalingConfigForm"
          class="auto-form"
          :label-width="0"
          form-type="inline"
        >
          <bk-form-item
            property="minReplicas"
            error-display-type="normal"
          >
            <bk-input
              type="number"
              class="dia-input"
              v-model="scalingConfig.minReplicas"
              disabled
            >
              <template slot="prepend">
                <div class="group-text">{{ $t('最小副本数') }}</div>
              </template>
            </bk-input>
          </bk-form-item>
          <bk-form-item
            property="maxReplicas"
            error-display-type="normal"
            class="ml20"
          >
            <bk-input
              type="number"
              class="dia-input"
              v-model="scalingConfig.maxReplicas"
              disabled
            >
              <template slot="prepend">
                <div class="group-text">{{ $t('最大副本数') }}</div>
              </template>
            </bk-input>
          </bk-form-item>
        </bk-form>
      </div>
    </div>
  </bk-dialog>
</template>

<script>
import i18n from '@/language/i18n.js';
let maxReplicasNum = 0;
export default {
  name: 'MigrationScalingDialog',
  model: {
    prop: 'value',
    event: 'change',
  },
  props: {
    value: {
      type: Boolean,
      default: false,
    },
    data: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      processConfigDialog: {
        visible: false,
        isLoading: false,
        showForm: true,
      },
      curTargetReplicas: 0,
      processPlan: {
        processType: 'unkonwn',
        targetReplicas: 0,
        maxReplicas: 0,
      },
      // 手动输入校验
      processPlanRules: {
        targetReplicas: [
          {
            required: true,
            message: i18n.t('请填写实例数'),
            trigger: 'blur',
          },
          {
            regex: /^[1-9][0-9]*$/,
            message: i18n.t('请填写大于0的整数'),
            trigger: 'blur',
          },
          {
            validator(val) {
              return val <= maxReplicasNum;
            },
            message() {
              return `${i18n.t('实例数不能大于最大上限')}${maxReplicasNum}`;
            },
            trigger: 'blur',
          },
        ],
      },
      // 当前扩缩容模式
      autoscaling: false,
      // 自动扩缩容数据
      scalingConfig: {
        minReplicas: 0,
        maxReplicas: 0,
      },
      maxReplicasNum: 0,
      defaultUtilizationRate: '85%',
      autoScalingTip: {
        theme: 'light',
        allowHtml: true,
        content: this.$t('提示信息'),
        html: `<a target="_blank" href="${
          this.GLOBAL.LINK.BK_APP_DOC
        }topics/paas/paas3_autoscaling" style="color: #3a84ff">${this.$t('查看动态扩缩容计算规则')}</a>`,
        placements: ['right'],
      },
    };
  },
  computed: {
    shrinkLimit() {
      return `${(((this.curTargetReplicas - 1) / this.curTargetReplicas) * 85).toFixed(1)}%`;
    },
  },
  watch: {
    value(newVal) {
      this.processConfigDialog.visible = newVal;
      if (newVal) {
        this.initData();
      }
    },
  },
  methods: {
    initData() {
      this.autoscaling = this.data.autoscaling;
      // 当前副本数
      this.curTargetReplicas = this.data.success;
      this.processPlan.targetReplicas = this.data.success;
      // 最大副本数
      maxReplicasNum = this.data.maxReplicas;
      // 自动调节
      if (this.autoscaling) {
        const { scalingConfig = {} } = this.data;
        this.scalingConfig.minReplicas = scalingConfig.min_replicas;
        this.scalingConfig.maxReplicas = scalingConfig.max_replicas;
      }
    },
    // 扩缩容校验
    handleConfirm() {
      if (!this.autoscaling) {
        // 手动调节
        this.$refs.manualAdjustmentForm.validate().then(
          () => {
            this.updateProcessConfig();
          },
          (validator) => {
            console.error(validator);
          }
        );
      }
    },
    // 更新扩缩容
    async updateProcessConfig() {
      // 没变化无需接口请求
      if (this.curTargetReplicas === this.processPlan.targetReplicas) {
        this.handleCancel();
        return;
      }
      this.processConfigDialog.isLoading = true;
      const { appCode, moduleId, env, type } = this.data;
      const patchData = {
        process_type: type,
        operate_type: 'scale',
      };
      if (!this.autoscaling) {
        // 进程副本数
        patchData.target_replicas = this.processPlan.targetReplicas;
      }
      try {
        await this.$store.dispatch('migration/updateProcess', {
          appCode,
          moduleId,
          env,
          data: patchData,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('扩缩容策略已更新'),
        });
        this.handleCancel();
        // 获取进程列表
        this.$emit('get-process-list');
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.processConfigDialog.isLoading = false;
      }
    },
    // 取消
    handleCancel() {
      this.handleAfterLeave();
    },
    handleAfterLeave() {
      this.$emit('change', false);
      this.$refs.manualAdjustmentForm?.clearError();
    },
  },
};
</script>

<style lang="scss" scoped>
.bk-form-control .group-box .group-text {
  line-height: 32px;
}
.rate-container {
  display: flex;
  align-items: center;
  .w80 {
    width: 80px;
  }
}
.radio-cls {
  /deep/ .bk-radio-button-text {
    padding: 0 102px;
  }
}
.desc-container {
  background: #f0f1f5;
  padding: 10px 20px;
  .cpu-num {
    color: #ff9c01;
    font-weight: 700;
  }
}
.dia-input {
  width: 250px;
}
.auto-container {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #dcdee5;
  .auto-form {
    display: flex;
    // width: 280px;
    /deep/ .bk-form-content .form-error-tip {
      padding-left: 90px !important;
    }
  }
}
</style>
