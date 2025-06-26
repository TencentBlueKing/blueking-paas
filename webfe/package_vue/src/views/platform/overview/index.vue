<template>
  <div class="right-main platform-overview">
    <div class="top-tools flex-row justify-content-between">
      <bk-input
        v-model="searchValue"
        :placeholder="$t('搜索租户')"
        :right-icon="'bk-icon icon-search'"
        style="width: 480px"
        clearable
      ></bk-input>
      <div class="right-legend flex-row align-items-center">
        <div>
          <IconStatus :configured="true" />
          {{ $t('已配置') }}
        </div>
        <div>
          <IconStatus :configured="false" />
          {{ $t('未配置') }}
        </div>
      </div>
    </div>
    <bk-table
      :data="displayTenants"
      v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
      border
      :key="tableKey"
    >
      <bk-table-column
        :label="$t('租户')"
        prop="tenant_name"
        label-class-name="special-head-column-cls"
      ></bk-table-column>
      <bk-table-column
        :label="$t('应用集群')"
        class-name="custom-column-td"
        label-class-name="special-head-column-cls"
      >
        <template #default="{ row }">
          <div :class="['cell-child-cls', { 'not-configured': !row.cluster?.allocated }]">
            <IconStatus :configured="row.cluster?.allocated" />
            <bk-button
              :text="true"
              title="primary"
              style="padding: 0"
              size="small"
              class="config-btn"
              @click="handleGoConfig('cluster')"
            >
              {{ $t('去配置') }}
            </bk-button>
          </div>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('增强服务')"
        label-class-name="add-ons-cls"
      >
        <bk-table-column
          v-for="item in services"
          :label="item.display_name"
          :key="item.id"
          class-name="custom-column-td"
          :render-header="$renderHeader"
          #default="{ row }"
        >
          <div :class="['cell-child-cls', { 'not-configured': !bindMap[row.tenant_id]?.[item.uuid] }]">
            <IconStatus :configured="bindMap[row.tenant_id]?.[item.uuid]" />
            <bk-button
              :text="true"
              title="primary"
              style="padding: 0"
              size="small"
              class="config-btn"
              @click="handleGoConfig('service')"
            >
              {{ $t('去配置') }}
            </bk-button>
          </div>
        </bk-table-column>
      </bk-table-column>
    </bk-table>
  </div>
</template>

<script>
import IconStatus from './components/icon-status.vue';
export default {
  name: 'PlatformOverview',
  components: {
    IconStatus,
  },
  data() {
    return {
      isLoading: true,
      searchValue: '',
      tenants: [],
      services: [],
      bindMap: {},
      tableKey: 0,
    };
  },
  computed: {
    displayTenants() {
      return this.searchValue ? this.filterByKeyword(this.tenants) : this.tenants;
    },
  },
  created() {
    Promise.all([this.getOverviewServices(), this.getTenantConfigStatuses()]).finally(() => {
      this.bindMap = this.tenants.reduce((map, tenant) => {
        map[tenant.tenant_id] = tenant.addons_services.reduce((acc, addon) => {
          acc[addon.id] = addon.bind || false;
          return acc;
        }, {});
        return map;
      }, {});
      this.tableKey += 1;
      this.isLoading = false;
    });
  },
  methods: {
    filterByKeyword(list) {
      const lowerCaseKeyword = this.searchValue.toLocaleLowerCase();
      return list.filter(
        (item) =>
          item.tenant_id?.toLocaleLowerCase().includes(lowerCaseKeyword) ||
          item.tenant_name?.toLocaleLowerCase().includes(lowerCaseKeyword)
      );
    },
    // 获取增强服务column
    async getOverviewServices() {
      try {
        const res = await this.$store.dispatch('tenant/getOverviewServices');
        this.services = res;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 各个租户的配置状态（行数据）
    async getTenantConfigStatuses() {
      try {
        const res = await this.$store.dispatch('tenant/getTenantConfigStatuses');
        this.tenants = res;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    handleGoConfig(type) {
      const routeName = type === 'cluster' ? 'platformAppCluster' : 'platformAddOns';
      this.$router.push({
        name: routeName,
        query: {
          active: 'config',
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.platform-overview {
  padding: 24px;
  .top-tools {
    margin-bottom: 16px;
    .right-legend {
      gap: 16px;
      height: 32px;
      padding: 0 10px;
      font-size: 12px;
      background: #ffffff;
      box-shadow: 0 1px 2px 0 #0000000f;
      border-radius: 4px;
      /deep/ i.paasng-icon {
        transform: translateY(0px);
        font-size: 14px !important;
      }
    }
  }
  /deep/ .bk-table {
    .custom-column-td {
      .cell {
        padding: 0 12px;
      }
    }
    .bk-table-body {
      .is-first .cell {
        padding: 0 12px;
      }
      .cell {
        display: flex;
        align-items: center;
        height: 100%;
      }
      .custom-column-td {
        .cell {
          padding: 0;
        }
        .cell-child-cls {
          display: flex;
          align-items: center;
          gap: 4px;
          width: 100%;
          height: 100%;
          padding: 0 12px;
          .config-btn {
            white-space: nowrap;
            display: none;
          }
        }
        .not-configured:hover {
          background: #fdf4e8;
          .config-btn {
            display: block;
          }
        }
      }
    }
    .special-head-column-cls .cell {
      height: 100%;
      padding: 0 12px;
    }
    .add-ons-cls > .cell .bk-table-header-label {
      text-align: center;
      width: 100%;
    }
  }
}
</style>
