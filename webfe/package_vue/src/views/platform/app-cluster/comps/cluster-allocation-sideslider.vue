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
        <span>{{ $t('集群分配') }}</span>
        <span class="desc">{{ `${$t('租户')}：${data.id}` }}</span>
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
          :has-env="isAllocatedByEnv"
          ref="uniformForm"
          :data="data"
          :is-edit="isEdit"
        />
        <!-- 按规则分配 -->
        <RuleBasedForm
          v-else
          ref="ruleBasedForm"
          :types="conditionTypes"
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
import RuleBasedForm from './rule-based-form.vue';
import SwitchDisplay from '@/components/switch-display';
import UniformForm from './uniform-form.vue';
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
      // 条件类型
      conditionTypes: [],
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
      if (this.isEdit) {
        const { type, allocation_policy = {} } = this.curTenantData.policies;
        this.methodValue = type;
        this.isAllocatedByEnv = allocation_policy?.env_specific || false;
      }
      this.getClusterAllocationPolicyConditionTypes();
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
    async handleSubmit() {
      this.submitLoading = true;
      try {
        const parmas = {
          tenant_id: this.data.id,
          type: this.methodValue,
        };
        if (this.isUniform) {
          // 统一分配
          const { clusters, env_clusters } = await this.$refs.uniformForm?.validate();
          parmas.allocation_policy = {
            env_specific: this.isAllocatedByEnv,
            // 不按环境分配
            ...(this.isAllocatedByEnv ? {} : { clusters }),
            // 按环境分配
            ...(this.isAllocatedByEnv ? { env_clusters } : {}),
          };
        } else {
          const { flag, data } = await this.$refs.ruleBasedForm?.validate();
          if (!flag) {
            this.submitLoading = false;
            return;
          }
          // 分配规则
          parmas.allocation_precedence_policies = data.map((item) => {
            return {
              matcher: item.matcher.key && item.matcher.value ? { [item.matcher.key]: item.matcher.value } : {},
              policy: {
                env_specific: item.hasEnv,
                ...(item.hasEnv ? {} : { clusters: item.clusters }),
                ...(item.hasEnv ? { env_clusters: item.envClusters } : {}),
              },
            };
          });
        }
        if (this.isEdit) {
          this.updateClusterAllocationPolicies(parmas);
        } else {
          this.createClusterAllocationPolicies(parmas);
        }
      } catch (e) {
        console.error(e);
        this.submitLoading = false;
      }
    },
    // 创建集群分配策略
    async createClusterAllocationPolicies(data) {
      try {
        await this.$store.dispatch('tenant/createClusterAllocationPolicies', {
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('集群分配成功！'),
        });
        this.handleCancel();
        this.$emit('refresh');
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.submitLoading = false;
      }
    },
    // 更新集群策略
    async updateClusterAllocationPolicies(data) {
      try {
        await this.$store.dispatch('tenant/updateClusterAllocationPolicies', {
          id: this.curTenantData.policies?.id,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('集群分配成功！'),
        });
        this.handleCancel();
        this.$emit('refresh');
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
    // 获取分配条件类型
    async getClusterAllocationPolicyConditionTypes() {
      try {
        const res = await this.$store.dispatch('tenant/getClusterAllocationPolicyConditionTypes');
        this.conditionTypes = res;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.submitLoading = false;
      }
    },
    // 更新集群策略
    async updateClusterAllocationPolicies(data) {
      try {
        await this.$store.dispatch('tenant/updateClusterAllocationPolicies', {
          id: this.curTenantData.policies?.id,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('集群分配成功！'),
        });
        this.handleCancel();
        this.$emit('refresh');
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.submitLoading = false;
      }
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
