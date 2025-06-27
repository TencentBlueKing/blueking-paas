<template>
  <div class="service-plan-container">
    <section class="all-services">
      <ServiceList
        ref="servicesRef"
        @change="serviceChange"
      />
    </section>
    <div
      class="plan-content card-style"
      ref="contentRef"
    >
      <div class="top-bar flex-row justify-content-between">
        <div class="flex-row left">
          <div
            class="capsule-tab-wrapper"
            v-if="tabData.length"
          >
            <TenantSelect
              v-model="curTenantId"
              :panels="tabData"
              :label="$t('所属租户')"
              :count-map="tenantPlanCountMap"
            />
          </div>
          <bk-button
            :theme="'primary'"
            icon="plus"
            class="ml10 flex-shrink-0"
            @click="showSideslider('add')"
          >
            {{ $t('添加方案') }}
          </bk-button>
        </div>
        <bk-input
          style="width: 350px"
          class="ml10 flex-shrink-0"
          :clearable="true"
          v-model="searchValue"
          :right-icon="'bk-icon icon-search'"
          :placeholder="$t('搜索方案名称')"
        ></bk-input>
      </div>
      <bk-table
        :data="searchPlans"
        dark-header
        size="small"
        :max-height="tableHeight"
        class="plan-table-cls"
        v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
      >
        <bk-table-column
          :label="$t('方案名称')"
          prop="name"
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            <bk-button
              :text="true"
              title="primary"
              @click="showPlanDetails(row, 'planBaseInfo')"
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
              class="paas-vue-json-pretty-cls"
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
          :width="120"
          show-overflow-tooltip
          :render-header="$renderHeader"
        ></bk-table-column>
        <bk-table-column
          :label="$t('资源池')"
          :width="80"
          show-overflow-tooltip
          :render-header="$renderHeader"
          v-if="activeService.origin === 'local'"
        >
          <template slot-scope="{ row }">
            <bk-button
              v-if="row.service_config?.provider_name === 'pool'"
              :text="true"
              title="primary"
              @click="showPlanDetails(row, 'planResourcePool')"
            >
              {{ row.pre_created_instances?.length || 0 }}
            </bk-button>
            <span v-else>{{ row.pre_created_instances?.length || 0 }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('是否可见')"
          prop="name"
          :width="80"
          show-overflow-tooltip
          :render-header="$renderHeader"
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
    <!-- 方案详情、资源池 -->
    <PlanDetailSideslider
      :show.sync="planDetailsConfig.isShow"
      :data="planDetailsConfig.row"
      :tenant-id="curTenantId"
      :services="platformServices"
      :active="planDetailsConfig.active"
      @refresh="getPlans"
    />
  </div>
</template>

<script>
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
import PlanSideslider from './plan-sideslider.vue';
import PlanDetailSideslider from './plan-detail-sideslider';
import ServiceList from '../service-config/service-list';
import TenantSelect from './tenant-select';
export default {
  name: 'ServicePlan',
  components: {
    VueJsonPretty,
    PlanSideslider,
    PlanDetailSideslider,
    ServiceList,
    TenantSelect,
  },
  props: {
    tenants: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      searchValue: '',
      isTableLoading: false,
      // 方案
      planList: [],
      // 服务
      platformServices: [],
      // 当期高亮的租户id
      curTenantId: '',
      // 新建/编辑侧栏
      isShowPlanSideslider: false,
      sidesliderConfig: {
        row: {},
        type: '',
      },
      // 详情侧拉
      planDetailsConfig: {
        isShow: false,
        row: {},
        active: '',
      },
      resizeObserver: null,
      tableHeight: 500,
      activeServiceId: '',
      activeService: {},
      tenantPlanCountMap: {},
    };
  },
  created() {
    this.getPlans();
  },
  mounted() {
    this.initResizeObserver();
  },
  beforeDestroy() {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
  },
  computed: {
    // 当前租户下的方案
    displayPlans() {
      return this.planList.filter((item) => item.tenant_id === this.curTenantId);
    },
    // 字段搜索、服务名、租户模式过滤
    searchPlans() {
      const { searchValue, activeServiceId, activeType, displayPlans = [] } = this;
      const lowerCaseSearchTerm = searchValue?.toLocaleLowerCase() || '';
      return displayPlans
        .filter((item) => !activeServiceId || item.service_id === activeServiceId)
        .filter((item) => !activeType || item.type === activeType)
        .filter((item) => !lowerCaseSearchTerm || (item.name?.toLocaleLowerCase() || '').includes(lowerCaseSearchTerm));
    },
    tabData() {
      return this.tenants.map((item) => {
        return {
          name: item.id,
          label: item.name,
        };
      });
    },
  },
  watch: {
    tenants: {
      handler(newList) {
        const tenantId = this.$route.params?.tenantId;
        this.curTenantId = tenantId || newList[0]?.id;
      },
      immediate: true,
    },
  },
  methods: {
    // 获取全量服务方案
    async getPlans() {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('tenant/getPlans');
        this.planList = res;
        this.tenantPlanCountMap = res.reduce((acc, item) => {
          const tenantId = item.tenant_id;
          acc[tenantId] = (acc[tenantId] || 0) + 1;
          return acc;
        }, {});
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        setTimeout(() => {
          this.isTableLoading = false;
        }, 20);
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
    // 新建/编辑方案侧栏
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
              serviceId: row.service_id,
              tenantId: this.curTenantId,
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
    // 方案详情-侧栏
    showPlanDetails(row, active) {
      this.getPlatformServices();
      this.planDetailsConfig.isShow = true;
      this.planDetailsConfig.row = row;
      this.planDetailsConfig.active = active;
    },
    initResizeObserver() {
      this.resizeObserver = new ResizeObserver((entries) => {
        window.requestAnimationFrame(() => {
          // 使用 requestAnimationFrame 延迟更新
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
    // 切换服务
    serviceChange(data) {
      this.activeService = data;
      this.activeServiceId = data.uuid;
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
    .top-bar {
      .left {
        flex: 1;
        min-width: 0;
      }
      .capsule-tab-wrapper {
        min-width: 0;
      }
    }
  }
}
</style>
