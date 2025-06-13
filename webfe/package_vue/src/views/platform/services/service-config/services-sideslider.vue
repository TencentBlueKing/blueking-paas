<template>
  <bk-sideslider
    :is-show.sync="sidesliderVisible"
    :quick-close="true"
    width="640"
    show-mask
    ext-cls="cluster-allocation-sideslider-cls"
    :before-close="handleBeforeClose"
    @shown="handleShown"
    @hidden="handleHidden"
  >
    <div slot="header">
      <div class="header-box">
        <span>{{ $t('配置服务') }}</span>
        <span class="desc">{{ `${$t('租户')}：${data.tenant_id}` }}</span>
      </div>
    </div>
    <div
      class="sideslider-content-cls"
      ref="sideslider"
      slot="content"
    >
      <div
        class="cluster-sideslider-main"
        ref="sidesliderMain"
      >
        <!-- 统一分配 -->
        <bk-form
          :label-width="200"
          form-type="vertical"
        >
          <bk-form-item
            :label="$t('分配方式')"
            :required="true"
          >
            <SwitchDisplay
              class="switch-cls"
              :list="methodList"
              :active="methodValue"
              @change="handlerChange"
            />
            <p
              class="select-env"
              v-if="isUniform"
            >
              <bk-checkbox v-model="isAllocatedByEnv">{{ $t('按环境分配') }}</bk-checkbox>
            </p>
          </bk-form-item>
        </bk-form>
        <!-- 统一分配 -->
        <UniformForm
          v-if="isUniform"
          ref="uniformForm"
          :has-env="isAllocatedByEnv"
          :data="data"
          :is-edit="isEdit"
          :label-text="label"
          :tips="tips"
          sideslider-type="plan"
        />
        <!-- 按规则分配 -->
        <RuleBasedForm
          v-else
          ref="ruleBasedForm"
          :types="conditionTypes"
          :label-text="label"
          :tips="tips"
          sideslider-type="plan"
        />
      </div>
      <div
        slot="footer"
        class="footer-btns"
      >
        <bk-button
          :theme="'primary'"
          class="mr8"
          :loading="submitLoading"
          @click="handleSubmit"
        >
          {{ $t('保存') }}
        </bk-button>
        <bk-button
          :theme="'default'"
          @click="handleCancel"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </div>
  </bk-sideslider>
</template>

<script>
import RuleBasedForm from '../../app-cluster/comps/rule-based-form.vue';
import SwitchDisplay from '../../app-cluster/comps/switch-display.vue';
import UniformForm from '../../app-cluster/comps/uniform-form.vue';
import sidebarDiffMixin from '@/mixins/sidebar-diff-mixin';
export default {
  name: 'ClusterAllocationSideslider',
  components: {
    SwitchDisplay,
    RuleBasedForm,
    UniformForm,
  },
  mixins: [sidebarDiffMixin],
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    data: {
      type: Object,
      default: () => ({}),
    },
    type: {
      type: String,
      default: 'new',
    },
  },
  data() {
    return {
      formData: {
        method: '',
        cluster: '',
      },
      methodList: [
        { name: 'uniform', label: this.$t('统一分配') },
        { name: 'rule_based', label: this.$t('按规则分配') },
      ],
      methodValue: 'uniform',
      isAllocatedByEnv: false,
      submitLoading: false,
      resizeObserver: null,
      // 条件类型-方案规则为固定值
      conditionTypes: [
        { key: 'regions', name: 'region_in' },
        { key: 'cluster_names', name: 'cluster_in' },
      ],
      label: '方案',
      tips: '如果配置多个方案：开发者启用增强服务时需要根据 “方案名称” 选择具体的增强服务方案；如开发者未选择任何值，则默认使用已选列表中的第一个方案。',
    };
  },
  computed: {
    sidesliderVisible: {
      get: function () {
        return this.show;
      },
      set: function (val) {
        this.$emit('update:show', val);
      },
    },
    isUniform() {
      return this.methodValue === 'uniform';
    },
    isEdit() {
      return this.type === 'edit';
    },
    curTenantData() {
      return this.$store.state.tenant.curTenantData;
    },
    availableClusters() {
      return this.$store.state.tenant.availableClusters;
    },
    plansMap() {
      return this.availableClusters.reduce((map, item) => {
        map[item.name] = item.uuid;
        return map;
      }, {});
    },
  },
  beforeDestroy() {
    // 停止观察
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }
  },
  methods: {
    handleShown() {
      // 处理类型
      if (this.isEdit) {
        const { type, allocation_policy = {} } = this.curTenantData.policies;
        this.methodValue = type;
        this.isAllocatedByEnv = !!allocation_policy.env_specific;
      }
      this.$nextTick(() => {
        this.setupResizeObserver();
        // 打开侧栏时，获取当前侧栏数据
        const initSidebarData = this.getCurrentStatusSidebarData();
        this.initSidebarFormData(initSidebarData);
      });
    },
    handleCancel() {
      this.sidesliderVisible = false;
    },
    handleHidden() {
      this.methodValue = 'uniform';
      this.submitLoading = false;
    },
    setupResizeObserver() {
      const element = this.$refs.sidesliderMain;
      if (!element) return;
      // 创建并设置观察者
      this.resizeObserver = new ResizeObserver(() => {
        this.checkForScrollbar(element);
      });
      this.resizeObserver.observe(element);
    },
    // 是否存在滚动条
    checkForScrollbar(element) {
      const hasVerticalScrollbar = element.scrollHeight > element.clientHeight;
      const hasHorizontalScrollbar = element.scrollWidth > element.clientWidth;
      if (hasVerticalScrollbar || hasHorizontalScrollbar) {
        this.addClass();
      } else {
        this.removeClass();
      }
    },
    addClass() {
      const element = this.$refs.sideslider;
      if (element) {
        element.classList.add('scroll');
      }
    },
    removeClass() {
      const element = this.$refs.sideslider;
      if (element) {
        element.classList.remove('scroll');
      }
    },
    // 切换分配方式
    handlerChange(item) {
      this.methodValue = item.name;
    },
    // 创建/编辑方案
    async handleSubmit() {
      this.submitLoading = true;
      try {
        const params = this.isUniform ? await this.formatUniformParams() : await this.formatRuleBasedParams();
        this.editOrAddConfigurationPlan(params);
      } catch (e) {
        console.warn(e);
        this.submitLoading = false;
      }
    },
    // 生成环境计划配置
    generateEnvPlans(envClusters) {
      return {
        prod: this.mapPlanNamesToIds(envClusters?.prod),
        stag: this.mapPlanNamesToIds(envClusters?.stag),
      };
    },
    // 转换方案名称到ID
    mapPlanNamesToIds(names = []) {
      return names.map((name) => this.plansMap[name]).filter(Boolean);
    },
    // 处理统一分配数据
    async formatUniformParams() {
      const { clusters, env_clusters: envClusters } = await this.$refs.uniformForm?.validate();
      return {
        tenant_id: this.curTenantData.policies.id,
        allocation_precedence_policies: null,
        allocation_policy: {
          ...(this.isAllocatedByEnv && {
            env_plans: this.generateEnvPlans(envClusters),
          }),
          ...(!this.isAllocatedByEnv && {
            plans: this.mapPlanNamesToIds(clusters),
          }),
        },
        policy_type: 'uniform',
      };
    },
    // 方案配置项
    generatePolicyConfig({ clusters, envClusters, hasEnv }) {
      return hasEnv ? { env_plans: this.generateEnvPlans(envClusters) } : { plans: this.mapPlanNamesToIds(clusters) };
    },
    // 处理规则分配数据
    async formatRuleBasedParams() {
      const { flag, data } = await this.$refs.ruleBasedForm?.validate();
      if (!flag) throw new Error(this.$t('必填项'));
      const policies = data.map((rule, index) => {
        const { matcher } = rule;
        const ruleItem = this.conditionTypes.find((v) => v.key === matcher.key);
        return {
          // 将方案name反转为id
          cond_type: ruleItem ? ruleItem.name : 'always_match',
          cond_data: ruleItem ? { [ruleItem.key]: matcher.value.split(',') } : {},
          priority: data.length - index,
          ...this.generatePolicyConfig(rule),
        };
      });
      return {
        tenant_id: this.curTenantData.policies.id,
        allocation_precedence_policies: policies,
        allocation_policy: null,
        policy_type: 'rule_based',
      };
    },
    // 创建/更新配置服务
    async editOrAddConfigurationPlan(data) {
      const dispatchName = this.isEdit ? 'updateBindingPolicies' : 'addBindingPolicies';
      const serviceId = this.curTenantData?.id;
      try {
        await this.$store.dispatch(`tenant/${dispatchName}`, {
          serviceId,
          data,
        });
        const message = this.isEdit ? this.$t('配置成功') : this.$t('添加成功');
        this.$paasMessage({
          theme: 'success',
          message,
        });
        this.handleCancel();
        this.$emit('refresh', serviceId);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.submitLoading = false;
      }
    },
    // 侧栏关闭前置检查，变更需要离开提示
    async handleBeforeClose() {
      const initSidebarData = this.getCurrentStatusSidebarData();
      return this.$isSidebarClosed(JSON.stringify(initSidebarData));
    },
    // 获取当前状态下的侧栏数据
    getCurrentStatusSidebarData() {
      const formRef = this.isUniform ? this.$refs.uniformForm : this.$refs.ruleBasedForm;
      const data = formRef?.getCurData();
      return {
        method: this.methodValue,
        ...data,
      };
    },
  },
};
</script>

<style lang="scss" scoped>
.header-box {
  .desc {
    height: 22px;
    margin-left: 10px;
    padding-left: 8px;
    font-size: 14px;
    color: #979ba5;
    border-left: 1px solid #dcdee5;
  }
}
.cluster-allocation-sideslider-cls {
  /deep/ .bk-sideslider-content {
    overflow: hidden;
    height: auto;
    max-height: calc(100vh - 52px) !important;
  }
  .footer-btns {
    z-index: 9;
    height: 48px;
    line-height: 48px;
    padding-left: 40px;
  }
}
.sideslider-content-cls {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  &.scroll {
    .footer-btns {
      background: #fafbfd;
      box-shadow: 0 -1px 0 0 #dcdee5;
    }
  }
}
.cluster-sideslider-main {
  padding: 24px 76px 22px 40px;
  max-height: calc(100vh - 100px);
  flex-shrink: 1;
  flex-grow: 1;
  overflow-y: auto;
  .switch-cls {
    /deep/ .group-item {
      padding: 0 20px;
    }
  }
  .select-env {
    margin: 12px 0;
  }
}
</style>
