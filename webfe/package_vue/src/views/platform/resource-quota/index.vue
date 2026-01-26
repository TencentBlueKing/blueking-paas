<template>
  <div class="resource-quota-container p-24">
    <bk-alert
      class="mb-16"
      type="info"
      :title="$t('资源方案添加后，应用将能够在“模块配置 - 进程配置”的资源配额方案中进行选择。')"
    ></bk-alert>
    <bk-button
      :theme="'primary'"
      icon="plus"
      @click="handleAddQuota"
    >
      {{ $t('添加方案') }}
    </bk-button>
    <bk-table
      ref="tableRef"
      :data="displayTemplateList"
      size="small"
      class="plan-table-cls mt-16"
      v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
    >
      <bk-table-column
        v-for="column in columns"
        v-bind="column"
        :label="$t(column.label)"
        :key="column.prop"
        show-overflow-tooltip
      >
        <template slot-scope="{ row }">
          <span v-if="column.prop === 'is_active'">
            <span v-bk-tooltips="builtinTooltipConfig(row)">
              <bk-switcher
                v-model="row.is_active"
                theme="primary"
                :disabled="row.is_builtin || updatingActiveIds[row.id]"
                @change="(value) => handleActiveChange(value, row)"
              ></bk-switcher>
            </span>
          </span>
          <span v-else>{{ getCellValue(row, column.prop) || '--' }}</span>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('操作')"
        :width="200"
      >
        <template slot-scope="{ row }">
          <span v-bk-tooltips="builtinTooltipConfig(row)">
            <bk-button
              theme="primary"
              text
              class="mr10"
              @click="handleEdit(row)"
              :disabled="row.is_builtin"
            >
              {{ $t('编辑') }}
            </bk-button>
          </span>
          <span v-bk-tooltips="builtinTooltipConfig(row)">
            <bk-button
              theme="primary"
              text
              @click="handleDelete(row)"
              :disabled="row.is_builtin"
            >
              {{ $t('删除') }}
            </bk-button>
          </span>
        </template>
      </bk-table-column>
    </bk-table>

    <!-- 添加/编辑方案侧边栏 -->
    <quota-plan-sideslider
      :visible.sync="showPlanSideslider"
      :edit-data="currentEditData"
      :cpu-options="cpuOptions"
      :memory-options="memoryOptions"
      @success="getResourceQuotaList"
    />
  </div>
</template>

<script>
import QuotaPlanSideslider from './quota-plan-sideslider.vue';

export default {
  name: 'ResourceQuota',
  components: {
    QuotaPlanSideslider,
  },
  data() {
    return {
      isLoading: false,
      showPlanSideslider: false,
      currentEditData: null,
      displayTemplateList: [],
      isTableLoading: false,
      cpuOptions: [],
      memoryOptions: [],
      // 用于记录正在更新状态的方案 ID（使用对象实现响应式）
      updatingActiveIds: {},
    };
  },
  computed: {
    columns() {
      return [
        {
          label: '方案名称',
          prop: 'name',
        },
        {
          label: 'CPU(Limits)',
          prop: 'limits.cpu',
        },
        {
          label: `${this.$t('内存')}(Limits)`,
          prop: 'limits.memory',
        },
        {
          label: 'CPU(Requests)',
          prop: 'requests.cpu',
        },
        {
          label: `${this.$t('内存')}(Requests)`,
          prop: 'requests.memory',
        },
        {
          label: '是否启用',
          prop: 'is_active',
          'render-header': this.renderHeader,
        },
      ];
    },
    // 内置方案禁用操作的 tooltip 配置
    builtinTooltipConfig() {
      return (row) => ({
        content: row.is_builtin ? this.$t('平台内置方案不支持操作') : '',
        disabled: !row.is_builtin,
      });
    },
  },
  created() {
    this.init();
  },
  methods: {
    // 初始化页面数据
    async init() {
      await Promise.all([this.getResourceQuotaList(), this.fetchQuantityOptions()]);
    },
    // 获取资源配额选项
    async fetchQuantityOptions() {
      try {
        const res = await this.$store.dispatch('tenantOperations/fetchQuantityOptions');
        this.cpuOptions = res.cpu_resource_quantity || [];
        this.memoryOptions = res.memory_resource_quantity || [];
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    renderHeader(h, data) {
      const directive = {
        name: 'bkTooltips',
        content: this.$t('停用后不影响已绑定的实例，但不能再绑定到新的应用'),
        placement: 'top',
      };
      return (
        <span
          class="custom-header-cell"
          v-bk-tooltips={directive}
        >
          {data.column.label}
        </span>
      );
    },
    // 获取单元格值(支持嵌套属性)
    getCellValue(row, prop) {
      if (!prop) return '';
      // 支持嵌套属性,如 'limits.cpu'
      const keys = prop.split('.');
      let value = row;
      for (const key of keys) {
        if (value && typeof value === 'object') {
          value = value[key];
        } else {
          return '';
        }
      }
      return value;
    },
    // 获取资源方案列表
    async getResourceQuotaList() {
      this.isLoading = true;
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('tenantConfig/getQuotaPlans');
        this.displayTemplateList = res || [];
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
        this.isTableLoading = false;
      }
    },
    // 添加资源方案
    handleAddQuota() {
      this.currentEditData = null;
      this.showPlanSideslider = true;
    },
    // 编辑资源方案
    handleEdit(row) {
      this.currentEditData = { ...row };
      this.showPlanSideslider = true;
    },
    // 删除弹窗确认
    handleDelete(row) {
      const h = this.$createElement;
      this.$bkInfo({
        title: this.$t('是否删除该项目方案？'),
        extCls: 'paas-custom-del-info-cls',
        theme: 'danger',
        width: 480,
        okText: this.$t('删除'),
        subHeader: h('div', [
          h('p', [h('span', { class: ['label'] }, `${this.$t('方案名称')}：`), h('span', row.name)]),
          h('div', { class: ['tips'] }, this.$t('删除后，应用将不能再绑定该方案，请谨慎操作')),
        ]),
        confirmFn: async () => {
          await this.deleteQuotaPlan(row);
        },
      });
    },
    // 删除资源方案
    async deleteQuotaPlan(row) {
      try {
        await this.$store.dispatch('tenantConfig/deleteQuotaPlan', { id: row.id });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除成功'),
        });
        this.getResourceQuotaList();
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 处理启用/停用状态变更
    async handleActiveChange(value, row) {
      // 添加到更新中的对象，禁用开关
      this.$set(this.updatingActiveIds, row.id, true);
      try {
        // 构建更新数据：只变更 is_active，其他参数保持不变
        const payload = {
          name: row.name,
          limits: {
            cpu: row.limits.cpu,
            memory: row.limits.memory,
          },
          requests: {
            cpu: row.requests.cpu,
            memory: row.requests.memory,
          },
          is_active: value,
        };

        await this.$store.dispatch('tenantConfig/updateQuotaPlan', {
          id: row.id,
          data: payload,
        });

        this.$paasMessage({
          theme: 'success',
          message: value ? this.$t('启用成功') : this.$t('停用成功'),
        });
      } catch (e) {
        // 更新失败，回滚状态
        row.is_active = !value;
        this.catchErrorHandler(e);
      } finally {
        // 从更新中的对象移除，恢复开关
        this.$delete(this.updatingActiveIds, row.id);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.resource-quota-container {
  /deep/ .bk-table-header .custom-header-cell {
    color: inherit;
    text-decoration: underline;
    text-decoration-style: dashed;
    text-underline-position: under;
  }
}
</style>
