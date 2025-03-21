<template>
  <div class="service-config-container">
    <!-- 服务列表 -->
    <ServiceList
      ref="servicesRef"
      :services="services"
      @change="serviceChange"
    />
    <div class="config-content card-style">
      <div class="top-box flex-row">
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
        dark-header
        :row-class-name="isConfigured"
        style="width: 100%"
        v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
        ext-cls="platform-table-cls"
      >
        <bk-table-column
          :label="$t('租户')"
          prop="tenant_id"
          width="160"
        ></bk-table-column>
        <bk-table-column
          :label="$t('方案')"
          class-name="cluster-allocation-cls"
        >
          <template slot-scope="{ row }">
            <!-- 未配置 -->
            <div
              v-if="!row.isConfig"
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
                v-if="!row.allocation_precedence_policies?.length"
                class="tag-list"
              >
                <!-- 按环境分配 env_specific -->
                <template v-if="row.allocation_policy?.env_plans">
                  <span class="tag">
                    {{ $t('集群（预发布环境）') }}：{{ getPlanNames(row.allocation_policy.env_plans.stag)?.join(', ') }}
                  </span>
                  <span class="tag">
                    {{ $t('集群（生产环境）') }}：{{ getPlanNames(row.allocation_policy.env_plans.prod)?.join(', ') }}
                  </span>
                </template>
                <!-- 不按环境分配 -->
                <template v-else>
                  <span
                    v-for="item in getPlanNames(row.allocation_policy.plans)"
                    class="tag"
                    :key="item"
                  >
                    {{ $t('集群') }}：{{ item }}
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
                  v-for="(item, i) in row?.displayPolicies"
                  :key="i"
                >
                  <!-- 一行规则 -->
                  <span class="tag if">
                    {{ getConditionalType(row?.displayPolicies?.length, i) }}
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
            v-if="row.isConfig"
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
      :data="operationRow"
      :type="sidesliderType"
      @refresh="getBindingPolicies"
    />
  </div>
</template>

<script>
import ServiceList from './service-list.vue';
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
      isTableLoading: false,
      // 所有服务
      services: [],
      bindingPolicies: [],
      plansMap: {},
      isShowSideslider: false,
      operationRow: {},
      sidesliderType: 'edit',
      // 当前服务id
      activeServiceId: '',
    };
  },
  computed: {
    displayBindingPolicies() {
      // 气泡按钮过滤 配置/未配置
      const filterCondition =
        this.filterValue === 'all'
          ? () => true
          : this.filterValue === 'notConfigured'
          ? (item) => !item.isConfig
          : (item) => item.isConfig;

      const filteredTable = this.bindingPolicies.filter(filterCondition);
      return this.searchValue ? this.filterByKeyword(filteredTable) : filteredTable;
    },
  },
  created() {
    this.getPlatformServices();
  },
  methods: {
    // 是否配置，未配置添加指定样式
    isConfigured({ row }) {
      return !row.isConfig ? 'cell-not-configured' : '';
    },
    // 关键字搜索
    filterByKeyword(list) {
      const lowerCaseKeyword = this.searchValue.toLocaleLowerCase();
      return list.filter((item) => item.tenant_id.toLocaleLowerCase().includes(lowerCaseKeyword));
    },
    handlerChange(data) {
      this.filterValue = data.name;
    },
    // 切换服务
    serviceChange(data) {
      this.activeServiceId = data.uuid;
      this.isTableLoading = true;
      Promise.all([this.getBindingPolicies(data.uuid), this.getPlansUnderService(data.uuid)]).finally(() => {
        this.isTableLoading = false;
      });
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
    // 获取服务下的方案
    async getPlansUnderService(serviceId) {
      try {
        const res = await this.$store.dispatch('tenant/getPlansUnderService', {
          serviceId,
        });
        for (let index = 0; index < res.length; index++) {
          this.$set(this.plansMap, res[index].uuid, res[index].name);
        }
        // 方案下拉框数据
        this.$store.commit('tenant/updateAvailableClusters', res);
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取服务列表
    async getPlatformServices() {
      try {
        const res = await this.$store.dispatch('tenant/getPlatformServices');
        this.services = res || [];
        this.$nextTick(() => {
          this.$refs.servicesRef?.handleSelected(res[0] || {});
        });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取服务下的绑定方案
    async getBindingPolicies(serviceId) {
      try {
        const response = await this.$store.dispatch('tenant/getBindingPolicies', { serviceId });

        // 创建租户策略映射表
        const tenantPolicyMap = response.reduce((map, policy) => ((map[policy.tenant_id] = policy), map), {});
        // 使用一次遍历完成数据转换和未配置计数
        let notConfiguredCount = 0;
        this.bindingPolicies = this.tenants.map((tenant) => {
          const policy = tenantPolicyMap[tenant.id];
          // 处理未配置情况
          if (!policy) {
            notConfiguredCount++;
            return {
              ...tenant,
              allocation_precedence_policies: [],
              allocation_policy: {},
              tenant_id: tenant.id,
              isConfig: false,
            };
          }
          // 处理已配置情况
          const { allocation_precedence_policies = [], allocation_policy = {} } = policy;
          // 创建排序后的新数组避免副作用
          const sortedPolicies = [...allocation_precedence_policies].sort((a, b) => b.priority - a.priority);
          return {
            ...tenant,
            ...policy,
            isConfig: true,
            displayPolicies: [...sortedPolicies, allocation_policy],
          };
        });
        // 计算过滤统计
        const totalCount = this.tenants.length;
        const configuredCount = totalCount - notConfiguredCount;

        this.filterList.forEach((filter) => {
          const { name } = filter;
          filter.count =
            {
              all: totalCount,
              notConfigured: notConfiguredCount,
              configured: configuredCount,
            }[name] ?? configuredCount; // 使用 nullish 操作符处理默认情况
        });
      } catch (error) {
        this.catchErrorHandler(error);
      }
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
      return isUniform
        ? this.handleUniformAllocation(row.allocation_policy)
        : this.handleRuleBasedAllocation(row.displayPolicies);
    },
    // 生成环境集群配置
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
    handleRuleBasedAllocation(displayPolicies) {
      return displayPolicies.map((item) => {
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
    handlerEdit(row, type) {
      // 如果为规则分配 allocation_policy 为 else 数据项，统一分配数据也是 allocation_policy
      const isUniform = !row.allocation_precedence_policies.length;
      const config = this.generateAllocationConfig(row, isUniform);
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
      this.sidesliderType = type;
      this.operationRow = row;
      this.isShowSideslider = true;
    },
    // 删除配置方案
    async handlerDelete(row) {
      this.$bkInfo({
        title: this.$t('确认删除服务配置'),
        confirmFn: async () => {
          try {
            await this.$store.dispatch('tenant/deleteBindingPolicies', {
              tenantId: row.tenant_id,
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
  },
};
</script>

<style lang="scss" scoped>
.service-config-container {
  height: 100%;
  display: flex;
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
