<template>
  <!-- 扩缩容弹窗 -->
  <bk-dialog
    v-model="scaleDialog.visible"
    header-position="left"
    theme="primary"
    :width="480"
    :mask-close="false"
    :title="$t(`${processPlan.processType}进程扩缩容`)"
  >
    <template #footer>
      <bk-button
        :theme="'primary'"
        :loading="isLoading"
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
    <div
      class="scaling-wrapper"
      v-bkloading="{ isLoading: isContentLoading, zIndex: 10 }"
    >
      <bk-form
        :model="scalingConfig"
        form-type="vertical"
        ref="scalingConfigForm"
      >
        <bk-form-item
          :label="$t('当前副本数：')"
          :label-width="90"
          ext-cls="horizontal-cls"
        >
          <span class="form-text">{{ processPlan.targetReplicas }}</span>
        </bk-form-item>
        <bk-form-item :label="$t('扩缩容方式')">
          <div class="tab-box">
            <li
              v-for="item in scaleTypes"
              :key="item.type"
              :class="['tab-item', { active: curActiveType === item.type },
                       { disabled: item.value && !autoScalDisableConfig.ENABLE_AUTOSCALING }]"
              @click="handleChangeType(item)"
            >
              {{ item.label }}
            </li>
          </div>
        </bk-form-item>
        <!-- 手动调节 -->
        <bk-form-item
          v-if="!autoscaling"
          property="targetReplicas"
          :label="$t('副本数量')"
          :rules="rules.targetReplicas"
          :error-display-type="'normal'"
        >
          <bk-input
            v-model="scalingConfig.targetReplicas"
            type="number"
            :max="5"
            :min="0"
            style="width: 216px"
          />
        </bk-form-item>
        <!-- 只读 -->
        <bk-form-item
          v-if="autoscaling"
          :label="$t('触发条件：')"
          :label-width="76"
          ext-cls="horizontal-cls"
        >
          <span class="form-text mr10">{{ $t('CPU 使用率') }} = 85%</span>
          <bk-icon
            class="info-circle-cls"
            type="info-circle"
            v-bk-tooltips="autoScalingTip"
          />
        </bk-form-item>
        <bk-form-item
          v-if="autoscaling"
          label=""
          :label-width="0"
        >
          <div class="trigger-tips-wrapper">
            <p>
              {{ $t('当 CPU 使用率') }} &gt;
              <span class="usage">85%</span>
              {{ $t('时，会触发扩容') }}
            </p>
            <p>
              {{ $t('当 CPU 使用率') }} &lt;
              <span class="usage">{{ shrinkLimit }}</span>
              {{ $t('时，会触发缩容') }}
            </p>
          </div>
        </bk-form-item>
        <div class="replica-count-cls">
          <bk-form-item
            v-if="autoscaling"
            property="minReplicas"
            :label="$t('最小副本数量')"
            :rules="rules.minReplicas"
            :error-display-type="'normal'"
          >
            <bk-input
              v-model="scalingConfig.minReplicas"
              type="number"
              :max="5"
              :min="0"
              style="width: 204px"
            />
          </bk-form-item>
          <bk-form-item
            v-if="autoscaling"
            property="maxReplicas"
            :label="$t('最大副本数量')"
            :rules="rules.maxReplicas"
            :error-display-type="'normal'"
          >
            <bk-input
              v-model="scalingConfig.maxReplicas"
              type="number"
              :max="5"
              :min="0"
              style="width: 204px"
            />
          </bk-form-item>
        </div>
      </bk-form>
    </div>
  </bk-dialog>
</template>

<script>import appBaseMixin from '@/mixins/app-base-mixin';
import i18n from '@/language/i18n.js';
import _ from 'lodash';
let maxReplicasNum = 0;

export default {
  name: 'ScaleDialog',
  mixins: [appBaseMixin],

  props: {
    value: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      environment: 'stag',
      moduleName: 'default',
      isLoading: false,
      isContentLoading: false,
      scaleDialog: {
        visible: false,
      },
      // false 手动 / true 自动
      autoscaling: false,
      scalingConfig: {
        targetReplicas: 0,
        minReplicas: 0,
        maxReplicas: 0,
        metrics: [
          {
            metric: 'cpuUtilization',
            value: '85',
          },
        ],
      },
      initScalingConfig: {},
      autoScalDisableConfig: {
        ENABLE_AUTOSCALING: false,
      },
      processPlan: {
        processType: 'unkonwn',
        targetReplicas: 0,
        maxReplicas: 0,
      },
      curActiveType: 'manual',
      scaleTypes: [
        { label: '手动调节', type: 'manual', value: false },
        { label: '自动调节', type: 'automatic', value: true },
      ],
      // CPU 使用率
      defaultUtilizationRate: '85%',
      processData: {},
      curTargetReplicas: 0,
      autoScalingTip: {
        theme: 'light',
        allowHtml: true,
        content: this.$t('提示信息'),
        html: `<a target="_blank" href="${this.GLOBAL.LINK.BK_APP_DOC}topics/paas/paas3_autoscaling" style="color: #3a84ff">${this.$t('动态扩缩容计算规则')}<i class="paasng-icon paasng-jump-link ml10"/></a>`,
        placements: ['top'],
      },
      rules: {
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
    };
  },

  computed: {
    shrinkLimit() {
      if (!this.curTargetReplicas) return '0%';
      return `${(((this.curTargetReplicas - 1) / this.curTargetReplicas) * 85).toFixed(1)}%`;
    },
  },

  watch: {
    value(val) {
      this.scaleDialog.visible = val;
    },
  },

  methods: {
    // 校验
    handleConfirm() {
      this.isLoading = true;
      setTimeout(async () => {
        try {
          const autoValidate = await this.$refs?.scalingConfigForm?.validate();
          if (autoValidate) {
            this.$store.commit('updataEnvEventData', []);
            this.updateProcessConfig();
          }
        } catch (error) {
          this.isLoading = false;
        }
      });
    },

    isScalingConfigChange() {
      return this.autoscaling === this.autoscalingBackUp
      && JSON.stringify(this.scalingConfig) === JSON.stringify(this.initScalingConfig);
    },

    // 进程实例设置
    async updateProcessConfig() {
      if (!this.autoscaling && this.scalingConfig.targetReplicas > this.processPlan.maxReplicas) {
        this.isLoading = false;
        return;
      }

      // 如果没有改变值也没有改变扩缩容方式不允许操作
      if (this.isScalingConfigChange()) {
        this.handleCancel();
        return;
      }

      const { processType } = this.processPlan;
      const planForm = {
        process_type: processType,
        operate_type: 'scale',
        target_replicas: this.scalingConfig.targetReplicas,
        autoscaling: this.autoscaling,
        scaling_config: {
          min_replicas: this.scalingConfig.minReplicas,
          max_replicas: this.scalingConfig.maxReplicas,
          metrics: this.scalingConfig.metrics,
        },
      };

      try {
        await this.$store.dispatch('processes/updateProcess', {
          appCode: this.appCode,
          moduleId: this.moduleName,
          env: this.environment,
          data: planForm,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('扩缩容策略已更新'),
        });
        this.$emit('updateStatus', this.scalingConfig.targetReplicas);
        this.scaleDialog.visible = false;
      } catch (err) {
        this.$paasMessage({
          theme: 'error',
          message: err.message,
        });
      } finally {
        this.isLoading = false;
      }
    },

    async getAutoScalFlag() {
      try {
        const res = await this.$store.dispatch('deploy/getAutoScalFlagWithEnv', {
          appCode: this.appCode,
          moduleId: this.moduleName,
          env: this.environment,
        });
        this.autoScalDisableConfig = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isContentLoading = false;
      }
    },

    // 添加校验规则
    addRules() {
      const that = this;
      const replicasRules = {
        maxReplicas: [
          {
            required: true,
            message: i18n.t('请填写最大副本数'),
            trigger: 'blur',
          },
          {
            regex: /^[1-9][0-9]*$/,
            message: i18n.t('请填写大于0的整数'),
            trigger: 'blur',
          },
          {
            validator(val) {
              const maxReplicas = Number(val);
              return maxReplicas <= maxReplicasNum;
            },
            message() {
              return `${i18n.t('最大副本数最大值')}${maxReplicasNum}`;
            },
            trigger: 'blur',
          },
          {
            validator(v) {
              const maxReplicas = Number(v);
              const minReplicas = Number(that.scalingConfig.minReplicas);
              return maxReplicas >= minReplicas;
            },
            message() {
              return `${i18n.t('最大副本数不可小于最小副本数')}`;
            },
            trigger: 'blur',
          },
        ],
        minReplicas: [
          {
            required: true,
            message: i18n.t('请填写最小副本数'),
            trigger: 'blur',
          },
          {
            regex: /^[1-9][0-9]*$/,
            message: i18n.t('请填写大于0的整数'),
            trigger: 'blur',
          },
          {
            validator(val) {
              const maxReplicas = Number(val);
              return maxReplicas <= maxReplicasNum;
            },
            message() {
              return `${i18n.t('最小副本数最大值')}${maxReplicasNum}`;
            },
            trigger: 'blur',
          },
          {
            validator(v) {
              const minReplicas = Number(v);
              const maxReplicas = Number(that.scalingConfig.maxReplicas);
              return minReplicas <= maxReplicas;
            },
            message() {
              return `${i18n.t('最小副本数不可大于最大副本数')}`;
            },
            trigger: 'blur',
            message() {
              return `${i18n.t('缩容下限不可大于扩容上限')}`;
            },
            trigger: 'blur',
          },
        ],
      };
      this.rules = Object.assign({}, replicasRules, this.rules);
    },

    // 切换扩容方式
    handleChangeType(data) {
      if (data.value && !this.autoScalDisableConfig.ENABLE_AUTOSCALING) {
        return;
      }
      this.curActiveType = data.type;
      this.autoscaling = data.value;
      // 数据重置
      this.scalingConfig.maxReplicas = this.initScalingConfig.maxReplicas;
      this.scalingConfig.minReplicas = this.initScalingConfig.minReplicas;
      this.scalingConfig.targetReplicas = this.initScalingConfig.targetReplicas;
      this.$refs.scalingConfigForm?.clearError();
    },

    // 取消
    handleCancel() {
      this.scaleDialog.visible = false;
      this.isLoading = false;
      this.autoscaling = false;
      this.scalingConfig.maxReplicas = 0;
      this.scalingConfig.minReplicas = 0;
      this.scalingConfig.targetReplicas = 0;
    },

    /**
     * 显示 dialog 初始化数据
     * @param process {Object} 当前进程数据
     * @param env {string} 环境
     */
    handleShowDialog(process, env = 'stag', moduleName) {
      this.environment = env;
      this.moduleName = moduleName;
      this.getAutoScalFlag();

      // 最大副本数
      maxReplicasNum = process.maxReplicas;
      const minReplicasNum = this.environment === 'prod' ? 2 : 1;

      this.processPlan = {
        replicas: process.instances?.length,
        processType: process.name,
        targetReplicas: process.available_instance_count,
        maxReplicas: process.maxReplicas,
      };

      // 扩容方式
      this.autoscaling = process.autoscaling;
      this.autoscalingBackUp = _.cloneDeep(this.autoscaling);
      this.curActiveType = process.autoscaling ? 'automatic' : 'manual';
      this.scalingConfig.maxReplicas = process?.scalingConfig?.max_replicas || maxReplicasNum;
      this.scalingConfig.minReplicas = process?.scalingConfig?.min_replicas || minReplicasNum;
      this.scalingConfig.targetReplicas = process.targetReplicas;

      this.initScalingConfig = { ...this.scalingConfig };
      console.log('this.processPlan', this.processPlan);
      this.curTargetReplicas = this.processPlan.targetReplicas;

      this.scaleDialog.visible = true;
      this.addRules();
    },
  },
};
</script>

<style lang="scss" scoped>
@import '~@/assets/css/mixins/customize-tab.scss';
@include tab-item(210px, 40px);

.scaling-wrapper {
  .tab-box {
    .tab-item:first-child {
      margin-right: 12px;
    }
  }
  .form-text {
    font-size: 14px;
    color: #313238;
  }
  .info-circle-cls {
    cursor: pointer;
    color: #979ba5;
  }
  .trigger-tips-wrapper {
    padding: 8px 16px;
    background: #f5f7fa;
    font-size: 12px;
    color: #63656e;
    .usage {
      font-weight: 700;
      color: #ff9c01;
    }
  }
  :deep(.horizontal-cls) {
    display: flex;
    align-items: center;
    .bk-label {
      padding-right: 0;
    }
    .bk-form-content {
      line-height: 32px;
      display: flex;
      align-items: center;
    }
  }
  :deep(.replica-count-cls) {
    display: flex;
    justify-content: space-between;
    .bk-form-item {
      margin-top: 8px;
    }
  }
}
</style>

<style lang="scss">
.trigger-conditions-cls .tippy-tooltip {
  padding: 8px;
  .bk-tooltip-content {
    transition: none;
    .content {
      cursor: pointer;
      color: #3a84ff;
    }
  }
}
</style>
