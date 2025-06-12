<template>
  <div class="service-config-container">
    <!-- 服务列表 -->
    <section class="all-services">
      <ServiceList
        v-bind="$attrs"
        ref="servicesRef"
        @change="serviceChange"
      />
    </section>
    <div
      class="config-content card-style"
      ref="contentRef"
    >
      <div class="top-box flex-row justify-content-between">
        <SwitchDisplay
          class="mr10"
          :list="filterList"
          :active="filterValue"
          :has-icon="true"
          :has-count="true"
          @change="handlerChange"
        />
        <bk-input
          v-model="searchValue"
          :placeholder="$t('搜索租户')"
          :right-icon="'bk-icon icon-search'"
          style="width: 480px"
        ></bk-input>
      </div>
      <bk-table
        :data="displayBindingPolicies"
        :size="'small'"
        :shift-multi-checked="true"
        :dark-header="true"
        :row-class-name="isConfigured"
        :max-height="tableHeight"
        style="width: 100%"
        v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
        ext-cls="platform-table-cls"
      >
        <bk-table-column
          :label="$t('租户')"
          prop="name"
          width="160"
        ></bk-table-column>
        <bk-table-column
          :label="$t('方案')"
          class-name="cluster-allocation-cls"
        >
          <template slot-scope="{ row }">
            <!-- 未配置 -->
            <div
              v-if="!row.policies"
              class="not-configured"
            >
              <span class="small-circle"></span>
              <span>{{ $t('未配置，将影响使用') }}，</span>
              <bk-button
                theme="primary"
                text
                @click="handlerEdit(row, 'add')"
              >
                {{ $t('配置') }}
              </bk-button>
            </div>
            <template v-else>
              <!-- 统一分配 -->
              <div
                v-if="row.policies?.policy_type === 'uniform'"
                class="tag-list"
              >
                <!-- 按环境分配 env_specific -->
                <template v-if="row.policies.allocation_policy?.env_plans">
                  <span class="tag">
                    {{ $t('方案（预发布环境）') }}：{{
                      getPlanNames(row.policies.allocation_policy.env_plans.stag)?.join(', ')
                    }}
                  </span>
                  <span class="tag">
                    {{ $t('方案（生产环境）') }}：{{
                      getPlanNames(row.policies.allocation_policy.env_plans.prod)?.join(', ')
                    }}
                  </span>
                </template>
                <!-- 不按环境分配 -->
                <template v-else>
                  <span
                    v-for="item in getPlanNames(row.policies.allocation_policy.plans)"
                    class="tag"
                    :key="item"
                  >
                    {{ $t('方案') }}：{{ item }}
                  </span>
                </template>
              </div>
              <!-- 按规则分配 -->
              <div
                v-else
                class="rules-list"
              >
                <div
                  class="row-rules"
                  v-for="(item, i) in row.policies?.allocation_precedence_policies"
                  :key="i"
                >
                  <!-- 一行规则 -->
                  <span class="tag if">
                    {{ getConditionalType(row.policies?.allocation_precedence_policies?.length, i) }}
                  </span>
                  <!-- 匹配规则 - 属性值不固定 -->
                  <span
                    v-for="(v, k) in item.cond_data"
                    class="tag rule"
                    :key="k"
                    v-show="v"
                  >
                    {{ `${k}=${v}` }}
                  </span>
                  <!-- 按环境-方案 -->
                  <template v-if="item?.env_plans">
                    <span class="tag">
                      {{ $t('方案（预发布环境）') }}：{{ getPlanNames(item.env_plans?.stag)?.join(', ') }}
                    </span>
                    <span class="tag">
                      {{ $t('方案（生产环境）') }}：{{ getPlanNames(item.env_plans?.prod)?.join(', ') }}
                    </span>
                  </template>
                  <template v-else>
                    <span
                      v-for="item in getPlanNames(item.plans)"
                      class="tag"
                      :key="item"
                    >
                      {{ $t('方案') }}：{{ item }}
                    </span>
                  </template>
                </div>
              </div>
            </template>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('操作')"
          width="150"
        >
          <template
            slot-scope="{ row }"
            v-if="row.policies"
          >
            <bk-button
              theme="primary"
              text
              @click="handlerEdit(row, 'edit')"
            >
              {{ $t('编辑') }}
            </bk-button>
            <bk-button
              theme="primary"
              class="ml10"
              text
              @click="handlerDelete(row)"
            >
              {{ $t('删除') }}
            </bk-button>
          </template>
        </bk-table-column>
      </bk-table>
    </div>
    <!-- 编辑服务方案 -->
    <ServicesSideslider
      :show.sync="isShowSideslider"
      :data="sidesliderConfig.row"
      :type="sidesliderConfig.type"
      @refresh="getBindingPolicies"
    />
  </div>
</template>

<script>
import ServiceList from './service-list';
import SwitchDisplay from '../../app-cluster/comps/switch-display.vue';
import ServicesSideslider from './services-sideslider.vue';
export default {
  components: { ServiceList, SwitchDisplay, ServicesSideslider },
  props: {
    tenants: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      filterValue: 'all',
      filterList: [
        { name: 'all', label: this.$t('全部'), count: 0 },
        { name: 'configured', label: this.$t('已配置'), count: 0 },
        { name: 'notConfigured', label: this.$t('未配置'), count: 0 },
      ],
      searchValue: '',
      isTableLoading: true,
      // 所有服务
      services: [],
      bindingPolicies: [],
      plansMap: {},
      isShowSideslider: false,
      sidesliderConfig: {
        row: {},
        type: 'edit',
      },
      // 当前服务id
      activeServiceId: '',
      isInit: false,
      tableHeight: 500,
      resizeObserver: null,
    };
  },
  computed: {
    displayBindingPolicies() {
      // 1. 按气泡按钮过滤（配置/未配置/全部）
      const filteredTable = this.filterBindingPolicies(this.bindingPolicies);
      // 2. 按关键词搜索（如果存在搜索值）
      return this.searchValue ? this.filterByKeyword(filteredTable) : filteredTable;
    },
  },
  mounted() {
    this.initResizeObserver();
  },
  beforeDestroy() {
    if (this.$refs.contentRef) {
      this.resizeObserver.unobserve(this.$refs.contentRef);
    }
  },
  methods: {
    // 是否配置，未配置添加指定样式
    isConfigured({ row }) {
      return !row.policies ? 'cell-not-configured' : '';
    },
    /**
     * 根据 filterValue 过滤策略列表
     */
    filterBindingPolicies(policies) {
      switch (this.filterValue) {
        case 'notConfigured':
          return policies.filter((item) => !item.policies);
        case 'configured':
          return policies.filter((item) => item.policies);
        default:
          return policies;
      }
    },
    // 关键字搜索
    filterByKeyword(list) {
      const lowerCaseKeyword = this.searchValue.toLocaleLowerCase();
      return list.filter((item) => item.name.toLocaleLowerCase()?.includes(lowerCaseKeyword));
    },
    handlerChange(data) {
      this.filterValue = data.name;
    },
    // 切换服务
    async serviceChange(data) {
      this.activeServiceId = data.uuid;
      this.isTableLoading = true;
      if (!this.isInit) {
        this.getPlans();
      }
      try {
        await this.getBindingPolicies(data.uuid);
      } finally {
        this.isTableLoading = false;
      }
    },
    // 获取当前规则语句分支
    getConditionalType(arrayLength, currentIndex) {
      if (currentIndex === 0) {
        return 'if';
      } else if (currentIndex === arrayLength - 1) {
        return 'else';
      } else {
        return 'else if';
      }
    },
    // 获取当前租户下服务-方案（select方案选择）
    async getServicePlansUnderTenant(tenantId, serviceId) {
      try {
        const res = await this.$store.dispatch('tenant/getServicePlansUnderTenant', {
          tenantId,
          serviceId,
        });
        // 方案下拉框数据
        this.$store.commit('tenant/updateAvailableClusters', res);
        return res;
      } catch (e) {
        this.catchErrorHandler(e);
        this.$store.commit('tenant/updateAvailableClusters', []);
        return [];
      }
    },
    // 获取所有服务方案
    async getPlans() {
      this.isInit = true;
      try {
        const res = await this.$store.dispatch('tenant/getPlans');
        for (let index = 0; index < res.length; index++) {
          this.$set(this.plansMap, res[index].uuid, res[index].name);
        }
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取服务下的绑定方案
    async getBindingPolicies(serviceId) {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('tenant/getBindingPolicies', { serviceId });

        // 创建租户ID到策略的映射
        const policyMap = new Map(res.map((policy) => [policy.tenant_id, policy]));

        // 数据处理，排序
        this.bindingPolicies = this.tenants
          .map((tenant) => ({
            ...tenant,
            policies: policyMap.get(tenant.id) || null,
          }))
          .sort((a, b) => {
            if (a.policies === null && b.policies !== null) {
              return -1;
            }
            if (a.policies !== null && b.policies === null) {
              return 1;
            }
            return 0;
          });

        // 获取已配置服务的租户ID集合
        const configuredTenantIds = new Set(res.map((service) => service.tenant_id));
        // 筛选未配置的租户
        const unconfiguredTenants = this.tenants.filter((tenant) => !configuredTenantIds.has(tenant.id));
        // 更新过滤统计
        this.updateFilterCounts(this.tenants.length, unconfiguredTenants.length);
      } catch (error) {
        this.catchErrorHandler(error);
      } finally {
        this.isTableLoading = false;
      }
    },
    updateFilterCounts(totalCount, notConfiguredCount) {
      const configuredCount = totalCount - notConfiguredCount;
      this.filterList.forEach((filter) => {
        filter.count =
          {
            all: totalCount,
            notConfigured: notConfiguredCount,
            configured: configuredCount,
          }[filter.name] ?? configuredCount;
      });
    },
    // 获取id对应的name
    getPlanNames(ids) {
      if (ids === null || !Array.isArray(ids)) {
        return [];
      }
      return ids.map((id) => {
        return this.plansMap[id];
      });
    },
    // 生成分配配置（统一/规则）
    generateAllocationConfig(row, isUniform) {
      if (row === null) {
        return isUniform ? {} : [];
      }
      return isUniform
        ? this.handleUniformAllocation(row.allocation_policy)
        : this.handleRuleBasedAllocation(row.allocation_precedence_policies);
    },
    // 生成环境方案配置
    generateEnvPlan(envPlans) {
      return envPlans
        ? {
            prod: this.getPlanNames(envPlans.prod),
            stag: this.getPlanNames(envPlans.stag),
          }
        : null;
    },
    // 处理统一分配配置
    handleUniformAllocation(allocationPolicy) {
      const { plans, env_plans } = allocationPolicy;
      return {
        clusters: this.getPlanNames(plans),
        env_clusters: this.generateEnvPlan(env_plans),
        env_specific: !!env_plans,
      };
    },
    // 处理规则分配配置
    handleRuleBasedAllocation(policies) {
      return policies.map((item) => {
        const key = Object.keys(item.cond_data || {})[0];
        return {
          matcher: {
            // cond_type：key、cond_data: { [name]: 输入框数据 }
            ...(item.cond_type && item.cond_data && key ? { [key]: item.cond_data[key]?.join(',') } : {}),
          },
          policy: {
            // 不按环境
            clusters: item.plans ? this.getPlanNames(item.plans) : null,
            // 按环境区分
            env_clusters: this.generateEnvPlan(item.env_plans),
            env_specific: !!item.env_plans,
          },
        };
      });
    },
    // 编辑/新建配置方案侧栏
    async handlerEdit(row, type) {
      const plans = await this.getServicePlansUnderTenant(row.id, this.activeServiceId);
      if (!plans.length) {
        this.showNoPlanInfo(row.id);
        return;
      }
      const isUniform = row.policies?.policy_type === 'uniform';
      const config = this.generateAllocationConfig(row.policies, isUniform);
      const commitData = {
        policies: {
          ...row,
          allocation_precedence_policies: isUniform ? [] : config,
          allocation_policy: isUniform ? config : {},
          type: isUniform ? 'uniform' : 'rule_based',
        },
        id: this.activeServiceId,
        isEdit: type === 'edit',
        type: 'plan',
      };
      // 设置侧栏需要的数据
      this.$store.commit('tenant/updateTenantData', commitData);
      this.sidesliderConfig.row = row;
      this.sidesliderConfig.type = type;
      this.isShowSideslider = true;
    },
    // 删除配置方案
    async handlerDelete(row) {
      this.$bkInfo({
        title: this.$t('确认删除服务配置'),
        confirmFn: async () => {
          try {
            await this.$store.dispatch('tenant/deleteBindingPolicies', {
              tenantId: row.id,
              serviceId: this.activeServiceId,
            });
            this.$paasMessage({
              theme: 'success',
              message: this.$t('删除成功'),
            });
            this.getBindingPolicies(this.activeServiceId);
            return true;
          } catch (e) {
            this.catchErrorHandler(e);
            return false;
          }
        },
      });
    },
    // 无方案弹窗提示
    showNoPlanInfo(tenantId) {
      const h = this.$createElement;
      // 如果没有集群，出现居中弹窗引导
      this.$bkInfo({
        type: 'warning',
        width: 480,
        title: this.$t('当前租户暂无可用方案'),
        subHeader: h(
          'div',
          {
            class: ['plan-info-header-cls'],
          },
          [
            h('p', { class: 'tip-text mb5' }, `${this.$t('您可以')}：`),
            h('p', { class: 'tip-text' }, this.$t('1. 在 [服务方案] 中添加新方案')),
          ]
        ),
        okText: this.$t('前往添加'),
        confirmFn: () => {
          // 跳转服务方案
          this.$router.push({ params: { tenantId }, query: { active: 'plan' } });
        },
      });
    },
    initResizeObserver() {
      this.resizeObserver = new ResizeObserver((entries) => {
        window.requestAnimationFrame(() => {
          for (let entry of entries) {
            if (entry.target === this.$refs.contentRef) {
              const height = entry.contentRect.height;
              this.tableHeight = height - 50;
            }
          }
        });
      });
      if (this.$refs.contentRef) {
        this.resizeObserver.observe(this.$refs.contentRef);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.plan-info-header-cls {
  text-align: left;
  font-size: 14px;
  padding: 8px 16px;
  color: #4d4f56;
  background: #f5f6fa;
  border-radius: 2px;
  .tip-text {
    line-height: 22px;
  }
}
.service-config-container {
  height: 100%;
  display: flex;
  .all-services {
    height: 100%;
  }
  .config-content {
    flex: 1;
    min-width: 0;
    padding: 16px;
  }
  .switch-group-container {
    flex-shrink: 0;
  }
  .platform-table-cls {
    margin-top: 16px;
    /deep/ .bk-table-body-wrapper .cell-not-configured {
      background: #fdf4e8;
    }
    .not-configured {
      color: #e38b02;
      .small-circle {
        display: inline-block;
        margin-right: 8px;
        width: 8px;
        height: 8px;
        background: #fce5c0;
        border: 1px solid #f59500;
        border-radius: 50%;
      }
    }
    .tag {
      display: inline-block;
      height: 22px;
      line-height: 22px;
      font-size: 12px;
      padding: 0 8px;
      color: #63656e;
      background: #f0f1f5;
      border-radius: 2px;
      &.if {
        color: #3a84ff;
        background: #edf4ff;
      }
      &.rule {
        color: #788779;
        background: #dde9de;
      }
    }
    .tag-list {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin: 10px 0;
    }
    .rules-list {
      margin: 10px 0;
      .row-rules {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-top: 4px;
        &:first-child {
          margin-top: 0;
        }
      }
    }
  }
}
</style>
