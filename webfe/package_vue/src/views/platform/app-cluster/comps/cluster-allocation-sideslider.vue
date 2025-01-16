<template>
  <bk-sideslider
    :is-show.sync="sidesliderVisible"
    :quick-close="true"
    width="640"
    @shown="handleShown"
  >
    <div slot="header">
      <div class="header-box">
        <span>{{ $t('集群分配') }}</span>
        <span class="desc">{{ `${$t('租户')}：${data.id}` }}</span>
      </div>
    </div>
    <div
      class="cluster-sideslider-content"
      slot="content"
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
      />
      <!-- 按规则分配 -->
      <RuleBasedForm v-else />
      <div class="btns">
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
          @click="sidesliderVisible = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </div>
  </bk-sideslider>
</template>

<script>
import RuleBasedForm from './rule-based-form.vue';
import SwitchDisplay from './switch-display.vue';
import UniformForm from './uniform-form.vue';
export default {
  name: 'ClusterAllocationSideslider',
  components: {
    SwitchDisplay,
    RuleBasedForm,
    UniformForm,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    data: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      formData: {
        method: '',
        cluster: '',
      },
      methodList: [
        { name: 'uniform', label: '统一分配' },
        { name: 'rule-based', label: '按规则分配' },
      ],
      methodValue: 'uniform',
      isAllocatedByEnv: false,
      submitLoading: false,
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
  },
  methods: {
    handleShown() {
      console.log('Shown');
    },
    handlerChange(item) {
      this.methodValue = item.name;
    },
    async handleSubmit() {
      // this.submitLoading = true;
      try {
        const parmas = {
          tenant_id: this.data.id,
          type: this.methodValue,
        };
        if (this.isUniform) {
          // 统一分配
          const { clusters, env_clusters } = await this.$refs.uniformForm?.validate();
          parmas.allocation_policy = {
            // 是否按环境分配
            env_specific: this.isAllocatedByEnv,
            // 不按环境分配
            clusters: this.isAllocatedByEnv ? null : clusters,
            // 按环境分配
            env_clusters: this.isAllocatedByEnv ? env_clusters : null,
          };
        } else {
          // 分配规则
          parmas.allocation_precedence_policies = [];
        }
        console.log('parmas', parmas);
      } catch (e) {
        console.error(e);
        this.submitLoading = false;
      }
    },
    // 创建集群分配策略
    async createClusterAllocationPolicies() {
      try {
        await this.$store.dispatch('tenant/createClusterAllocationPolicies');
      } catch (e) {
        this.catchErrorHandler(e);
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
.cluster-sideslider-content {
  padding: 24px 76px 0 40px;
  .switch-cls {
    /deep/ .group-item {
      padding: 0 20px;
    }
  }
  .select-env {
    margin: 12px 0;
  }
}
.btns {
  margin-top: 32px;
  .mr8 {
    margin-right: 8px;
  }
  .bk-button {
    padding: 0 30px;
  }
}
</style>
