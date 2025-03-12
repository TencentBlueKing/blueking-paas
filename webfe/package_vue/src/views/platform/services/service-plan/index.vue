<template>
  <div class="service-plan-container">
    <TenantsList
      :tenants="tenants"
      :loading="isTenantLoading"
      @change="handleChange"
    />
    <div class="plan-content card-style">
      <div class="flex-row justify-content-between">
        <bk-button
          :theme="'primary'"
          class="mr10"
          @click="showSideslider('add')"
        >
          {{ $t('添加方案') }}
        </bk-button>
        <bk-input
          style="width: 480px"
          :clearable="true"
          v-model="searchValue"
          :right-icon="'bk-icon icon-search'"
          :placeholder="$t('搜索方案名称、方案别名、所属方案')"
        ></bk-input>
      </div>
      <bk-table
        :data="displayPlans"
        dark-header
        size="small"
        class="plan-table-cls"
        v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
      >
        <bk-table-column
          :label="$t('方案名称')"
          prop="name"
          :width="140"
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            <bk-button
              :text="true"
              title="primary"
            >
              {{ row.name }}
            </bk-button>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('配置')"
          prop="conditions"
          :min-width="200"
        >
          <div slot-scope="{ row }">
            <!-- JSON格式预览 -->
            <vue-json-pretty
              :data="row.config"
              :deep="Object.keys(row.config)?.length ? 1 : 0"
              :show-length="true"
              :highlight-mouseover-node="true"
            />
          </div>
        </bk-table-column>
        <bk-table-column
          :label="$t('所属服务')"
          prop="service_name"
          :width="100"
          show-overflow-tooltip
        ></bk-table-column>
        <bk-table-column
          :label="$t('资源池')"
          :width="100"
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            <bk-button
              :text="true"
              title="primary"
            >
              {{ row.pre_created_instances?.length || 0 }}
            </bk-button>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('是否可见')"
          prop="name"
          :width="80"
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            <span :class="['tag', { yes: row.is_active }]">{{ row.is_active ? $t('是') : $t('否') }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('操作')"
          :width="100"
        >
          <template slot-scope="{ row }">
            <bk-button
              theme="primary"
              text
              class="mr10"
              @click="showSideslider('edit', row)"
            >
              {{ $t('编辑') }}
            </bk-button>
            <bk-button
              theme="primary"
              text
              @click="handleDelete(row)"
            >
              {{ $t('删除') }}
            </bk-button>
          </template>
        </bk-table-column>
      </bk-table>
    </div>

    <!-- 添加、编辑方案 -->
    <PlanSideslider
      :show.sync="isShowPlanSideslider"
      :tenant-id="curTenantId"
      :data="sidesliderConfig.row"
      :services="platformServices"
      :config="sidesliderConfig"
      @refresh="getPlans"
    />
  </div>
</template>

<script>
import TenantsList from './tenants-list.vue';
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
import PlanSideslider from './plan-sideslider.vue';
export default {
  name: 'ServicePlan',
  components: {
    TenantsList,
    VueJsonPretty,
    PlanSideslider,
  },
  data() {
    return {
      searchValue: '',
      isTableLoading: false,
      isTenantLoading: false,
      // 方案
      planList: [],
      // 租户
      tenants: [],
      // 服务
      platformServices: [],
      // 当期高亮的租户id
      curTenantId: '',
      isShowPlanSideslider: false,
      sidesliderConfig: {
        row: {},
        type: '',
      },
    };
  },
  created() {
    this.getTenants();
    this.getPlans();
  },
  computed: {
    displayPlans() {
      return this.planList.filter((item) => item.tenant_id === this.curTenantId);
    },
  },
  methods: {
    handleChange(tenantId) {
      // 请求租户下的方案
      this.curTenantId = tenantId;
    },
    // 获取所有租户
    async getTenants() {
      this.isTenantLoading = true;
      try {
        const res = await this.$store.dispatch('tenant/getTenants');
        this.tenants = res;
        this.curTenantId = res[0]?.id || '';
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isTenantLoading = false;
      }
    },
    // 获取全量服务方案
    async getPlans() {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('tenant/getPlans');
        this.planList = res;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isTableLoading = false;
      }
    },
    // 方案-所属服务
    async getPlatformServices() {
      try {
        const res = await this.$store.dispatch('tenant/getPlatformServices');
        this.platformServices = res || [];
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 新建/编辑
    showSideslider(type, row) {
      this.isShowPlanSideslider = true;
      this.sidesliderConfig.type = type;
      if (!this.platformServices.length) {
        this.getPlatformServices();
      }
      if (type === 'edit') {
        this.sidesliderConfig.row = row;
      }
    },
    // 删除方案
    handleDelete(row) {
      this.$bkInfo({
        title: this.$t('确认删除方案'),
        confirmFn: async () => {
          try {
            await this.$store.dispatch('tenant/deletePlan', {
              id: row.service_id,
              planId: row.uuid,
            });
            this.$paasMessage({
              theme: 'success',
              message: this.$t('删除成功'),
            });
            this.getPlans();
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
.service-plan-container {
  height: 100%;
  display: flex;
  .plan-content {
    flex: 1;
    min-width: 0;
    padding: 16px;
    .plan-table-cls {
      margin-top: 12px;
    }
    .tag.yes {
      background: #daf6e5;
      color: #299e56;
    }
  }
}
</style>
