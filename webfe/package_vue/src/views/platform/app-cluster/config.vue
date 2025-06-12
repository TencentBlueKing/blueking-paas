<template>
  <div class="platform-config">
    <paas-content-loader
      placeholder="platform-config-loading"
      class="platform-config-loading-cls"
      :offset-top="0"
      :is-loading="isContentLoading"
    >
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
        :data="displayPlatformList"
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
          prop="name"
          width="160"
        ></bk-table-column>
        <bk-table-column
          :label="$t('集群分配')"
          class-name="cluster-allocation-cls"
        >
          <template slot-scope="{ row }">
            <template v-if="row.policies">
              <!-- 统一分配 -->
              <div
                v-if="row.policies.type === 'uniform'"
                class="tag-list"
              >
                <!-- 按环境分配 env_specific -->
                <template v-if="row.policies.allocation_policy?.env_specific">
                  <span class="tag">
                    {{ $t('集群（预发布环境）') }}：{{ row.policies.allocation_policy.env_clusters.stag?.join(', ') }}
                  </span>
                  <span class="tag">
                    {{ $t('集群（生产环境）') }}：{{ row.policies.allocation_policy.env_clusters.prod?.join(', ') }}
                  </span>
                </template>
                <!-- 不按环境分配 -->
                <template v-else>
                  <span
                    v-for="item in row.policies.allocation_policy.clusters"
                    class="tag"
                    :key="`not-${item}`"
                  >
                    {{ $t('集群') }}：{{ item }}
                  </span>
                </template>
              </div>
              <!-- 按规则 -->
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
                  <!-- 匹配规则 -->
                  <span
                    v-for="(v, k) in item.matcher"
                    class="tag rule"
                    :key="`rule-${v}`"
                    v-show="v"
                  >
                    {{ `${matchingRulesMap[k]} = ${v}` }}
                  </span>
                  <!-- 集群-不按环境 -->
                  <template v-if="item.policy?.env_specific">
                    <span class="tag">
                      {{ $t('集群（预发布环境）') }}：{{ item.policy.env_clusters?.stag?.join(', ') }}
                    </span>
                    <span class="tag">
                      {{ $t('集群（生产环境）') }}：{{ item.policy.env_clusters?.prod?.join(', ') }}
                    </span>
                  </template>
                  <template v-else>
                    <span
                      v-for="item in item.policy.clusters"
                      class="tag"
                      :key="`uniform-${item}`"
                    >
                      {{ $t('集群') }}：{{ item }}
                    </span>
                  </template>
                </div>
              </div>
            </template>
            <div
              v-else
              class="not-configured"
            >
              <span class="small-circle"></span>
              <span>{{ $t('未配置，应用无法部署') }}，</span>
              <bk-button
                theme="primary"
                text
                @click="handleClusterAllocation(row, 'new')"
              >
                {{ $t('配置') }}
              </bk-button>
            </div>
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
              @click="handleClusterAllocation(row, 'edit')"
            >
              {{ $t('编辑') }}
            </bk-button>
            <bk-button
              theme="primary"
              text
              class="ml10"
              @click="handleAllocationPolicies(row)"
            >
              {{ $t('删除') }}
            </bk-button>
          </template>
        </bk-table-column>
      </bk-table>
    </paas-content-loader>
    <ClusterAllocationSideslider
      :show.sync="isShowSideslider"
      :data="operationRow"
      :type="sidesliderType"
      @refresh="init"
    />
  </div>
</template>

<script>
import { bus } from '@/common/bus';
import SwitchDisplay from './comps/switch-display.vue';
import ClusterAllocationSideslider from './comps/cluster-allocation-sideslider.vue';
export default {
  name: 'PlatformConfig',
  components: {
    SwitchDisplay,
    ClusterAllocationSideslider,
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
      isContentLoading: true,
      platformList: [],
      isShowSideslider: false,
      sidesliderType: '',
      operationRow: {},
      // 全量集群策略
      allPolicies: [],
      // 所有租户
      tenants: [],
      // 可用集群
      availableClusters: [],
      matchingRulesMap: {},
    };
  },
  created() {
    this.init();
  },
  computed: {
    displayPlatformList() {
      const filterCondition =
        this.filterValue === 'all'
          ? () => true
          : this.filterValue === 'notConfigured'
          ? (item) => !item.policies
          : (item) => item.policies;

      const filteredTable = this.platformList.filter(filterCondition);
      return this.searchValue ? this.filterByKeyword(filteredTable) : filteredTable;
    },
  },
  methods: {
    init() {
      this.isTableLoading = true;
      Promise.all([this.getTenants(), this.getClusterAllocationPolicies()]).finally(() => {
        // 将策略与租户数据重组
        this.platformList = this.tenants
          .map((tenant) => ({
            ...tenant,
            policies: this.allPolicies.find((v) => v.tenant_id === tenant.id) ?? null,
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
        this.filterList.forEach((v) => {
          if (v.name === 'all') {
            v.count = this.platformList.length;
          } else if (v.name === 'notConfigured') {
            v.count = this.platformList.filter((item) => !item.policies).length;
          } else {
            v.count = this.platformList.filter((item) => item.policies).length;
          }
        });
        this.isTableLoading = false;
        this.isContentLoading = false;
      });
      this.getClusterAllocationPolicyConditionTypes();
    },
    // 关键字搜索
    filterByKeyword(list) {
      const lowerCaseKeyword = this.searchValue.toLowerCase();
      return list.filter((item) => item.name.toLowerCase().includes(lowerCaseKeyword));
    },
    handlerChange(data) {
      this.filterValue = data.name;
    },
    // 是否配置，未配置添加指定样式
    isConfigured({ row }) {
      return !row.policies ? 'cell-not-configured' : '';
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
    // 获取所有租户
    async getTenants() {
      try {
        const res = await this.$store.dispatch('tenant/getTenants');
        this.tenants = res;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取全量集群策略，一个租户最多有一个策略
    async getClusterAllocationPolicies() {
      try {
        const res = await this.$store.dispatch('tenant/getClusterAllocationPolicies');
        this.allPolicies = res;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取当前租户可用的集群
    async getAvailableClusters(id) {
      try {
        const res = await this.$store.dispatch('tenant/getAvailableClusters', { id });
        this.availableClusters = res;
        // 存入store
        this.$store.commit('tenant/updateAvailableClusters', res);
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 集群分配
    async handleClusterAllocation(row, type) {
      this.$store.commit('tenant/updateTenantData', {
        ...row,
        isEdit: type === 'edit',
      });
      this.operationRow = row;
      // 前置判断是否存在可分配集群
      await this.getAvailableClusters(row.id);
      if (this.availableClusters.length) {
        this.sidesliderType = type;
        this.isShowSideslider = true;
        return;
      }
      const h = this.$createElement;
      // 如果没有集群，出现居中弹窗引导
      this.$bkInfo({
        type: 'warning',
        width: 480,
        title: this.$t('当前租户暂无可用集群'),
        subHeader: h(
          'div',
          {
            class: ['cluster-info-header-cls'],
          },
          [
            h('p', { class: 'tip-text mb5' }, `${this.$t('您可以')}：`),
            h('p', { class: 'tip-text' }, this.$t('1. 联系平台管理员，为当前租户分配可用集群')),
            h('p', { class: 'tip-text' }, this.$t('2. 在 [集群列表] 中添加新集群')),
          ]
        ),
        okText: this.$t('前往添加'),
        confirmFn: () => {
          // 跳转集群列表
          bus.$emit('tool-table-change', 'list');
        },
      });
    },
    // 获取分配条件类型
    async getClusterAllocationPolicyConditionTypes() {
      try {
        const res = await this.$store.dispatch('tenant/getClusterAllocationPolicyConditionTypes');
        res.forEach((v) => {
          this.matchingRulesMap[v.key] = v.name;
        });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 删除分配策略
    async handleAllocationPolicies(row) {
      this.$bkInfo({
        title: this.$t('确认删除租户 {k} 的集群分配策略？', { k: row.policies.tenant_id }),
        confirmLoading: true,
        width: 480,
        confirmFn: async () => {
          try {
            await this.$store.dispatch('tenant/delClusterAllocationPolicies', {
              id: row.policies?.id,
            });
            this.$paasMessage({
              theme: 'success',
              message: this.$t('删除成功'),
            });
            this.init();
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
.cluster-info-header-cls {
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
.platform-config {
  .platform-config-loading-cls {
    /deep/ .loading-placeholder {
      margin-top: 0 !important;
    }
  }
  .filter-group {
    width: fit-content;
    background: #eaebf0;
    display: flex;
    align-items: center;
    padding: 4px;
    .group-item {
      height: 24px;
      line-height: 24px;
      padding: 0 12px;
      font-size: 12px;
      background: #eaebf0;
      border-radius: 2px;
      cursor: pointer;
      transition: all 0.2s;
      &.active {
        background: #fff;
        color: #3a84ff;
      }
    }
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
</style>
