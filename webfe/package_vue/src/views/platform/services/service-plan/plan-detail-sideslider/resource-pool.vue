<template>
  <div class="resource-pool-container">
    <div class="flex-row justify-content-between">
      <bk-button
        :theme="'primary'"
        class="mr10"
        @click="addInstances"
      >
        {{ $t('添加实例') }}
      </bk-button>
    </div>
    <bk-table
      :data="instances"
      dark-header
      size="small"
      class="resource-pool-cls"
      v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
    >
      <bk-table-column
        :label="$t('实例凭证')"
        prop="conditions"
      >
        <template slot-scope="{ row }">
          <MaskedTextViewer
            :data="row.jsonData"
            :deep="Object.keys(row.jsonData)?.length ? 1 : 0"
            :plaintext.sync="plaintextStatusMap[`${row.uuid}-credentials`]"
          />
        </template>
      </bk-table-column>
      <bk-table-column :label="`TLS ${$t('配置')}`">
        <template slot-scope="{ row }">
          <template v-if="!row.tlsConfig">--</template>
          <MaskedTextViewer
            v-else
            :data="row.tlsConfig"
            :deep="Object.keys(row.tlsConfig)?.length ? 1 : 0"
            :plaintext.sync="plaintextStatusMap[`${row.uuid}-tls`]"
          />
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('已分配')"
        prop="name"
        :width="80"
        show-overflow-tooltip
      >
        <template slot-scope="{ row }">
          <span :class="['tag', { yes: row.is_allocated }]">{{ row.is_allocated ? $t('是') : $t('否') }}</span>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('可回收复用')"
        prop="name"
        :width="100"
        show-overflow-tooltip
        :render-header="$renderHeader"
      >
        <template slot-scope="{ row }">
          <!-- 字段待确认 -->
          <span :class="['tag', { yes: row.config?.recyclable }]">
            {{ row.config?.recyclable ? $t('是') : $t('否') }}
          </span>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('操作')"
        :width="140"
      >
        <template slot-scope="{ row }">
          <bk-button
            theme="primary"
            text
            class="mr10"
            @click="handleClone(row)"
          >
            {{ $t('克隆') }}
          </bk-button>
          <bk-button
            theme="primary"
            text
            class="mr10"
            @click="handleEdit(row)"
          >
            {{ $t('编辑') }}
          </bk-button>
          <bk-popconfirm
            trigger="click"
            ext-cls="sandbox-destroy-cls"
            width="180"
            @confirm="handleDelete(row)"
          >
            <div slot="content">
              <div class="custom">
                <i class="content-icon bk-icon icon-info-circle-shape pr5"></i>
                <span>{{ $t('确认删除实例？') }}</span>
              </div>
            </div>
            <bk-button
              theme="primary"
              text
            >
              {{ $t('删除') }}
            </bk-button>
          </bk-popconfirm>
        </template>
      </bk-table-column>
    </bk-table>

    <!-- 添加/编辑方案 -->
    <EditAddDialog
      ref="dialogRef"
      :show.sync="dialogConfig.isShow"
      :data="dialogConfig"
      @refresh="getPreCreatedInstances"
    />
  </div>
</template>

<script>
import EditAddDialog from './edit-add-dialog.vue';
import MaskedTextViewer from '@/components/masked-text-viewer';

export default {
  props: {
    data: {
      type: Object,
      default: () => ({}),
    },
    tenantId: {
      type: String,
      default: '',
    },
  },
  components: {
    MaskedTextViewer,
    EditAddDialog,
  },
  data() {
    return {
      isTableLoading: false,
      dialogConfig: {
        isShow: false,
        row: {},
        type: 'add',
        planId: '',
        service: '',
      },
      // 当前方案下的资源池
      instances: [],
      // 每行的明文/密文状态 { 'rowId-credentials': true/false, 'rowId-tls': true/false }
      plaintextStatusMap: {},
    };
  },
  created() {
    this.getPreCreatedInstances();
  },
  methods: {
    formatServiceName() {
      return `${this.data?.service_name?.toLocaleUpperCase()}_`;
    },
    // 添加实例
    addInstances() {
      this.dialogConfig.isShow = true;
      this.dialogConfig.type = 'add';
      this.dialogConfig.planId = this.data?.uuid;
      this.dialogConfig.service = this.formatServiceName();
    },
    // 格式化 tls 配置
    formatTlsConfig(config) {
      try {
        if (!config) {
          return null;
        }
        if (typeof config === 'string') {
          return JSON.parse(config);
        }
        return config;
      } catch (e) {
        console.error('TLS配置格式化失败', e);
      }
    },
    // 获取方案下的资源池
    async getPreCreatedInstances(isOperate = false) {
      if (isOperate) {
        // 新建/编辑操作
        this.$emit('operate');
      }
      this.isTableLoading = true;
      try {
        const ret = await this.$store.dispatch('tenant/getPreCreatedInstances', {
          serviceId: this.data?.service_id,
          tenantId: this.tenantId,
          planId: this.data?.uuid,
        });
        this.instances = ret?.pre_created_instances?.map((item) => {
          const tlsConfig = this.formatTlsConfig(item.config?.tls);
          return Object.assign(item, {
            jsonData: JSON.parse(item.credentials),
            tlsConfig,
          });
        });
        this.$emit('change', this.instances.length);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isTableLoading = false;
      }
    },
    // 编辑
    handleEdit(row) {
      this.dialogConfig = {
        isShow: true,
        row,
        type: 'edit',
        planId: row.plan_id,
        service: this.formatServiceName(),
      };
    },
    // 删除
    async handleDelete(row) {
      try {
        await this.$store.dispatch('tenant/deleteResourcePool', {
          planId: row.plan_id,
          id: row.uuid,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除成功'),
        });
        this.$emit('operate');
        this.getPreCreatedInstances();
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 克隆
    handleClone(row) {
      this.dialogConfig.planId = row?.plan_id;
      const { plan_id, credentials, config } = row;
      const params = {
        plan: plan_id,
        credentials,
        config,
      };
      this.$refs.dialogRef?.addResourcePool(params, true);
    },
  },
};
</script>

<style lang="scss" scoped>
.resource-pool-container {
  .resource-pool-cls {
    margin-top: 16px;
    /deep/ .bk-table-row.hover-row {
      .masked-text-viewer i.paasng-icon {
        display: block !important;
      }
    }
  }
}
.sandbox-destroy-cls {
  .custom {
    font-size: 14px;
    line-height: 24px;
    color: #63656e;
    padding-bottom: 16px;
    .content-icon {
      display: inline-block;
      transform: translateY(-1px);
      color: #ea3636;
    }
  }
}
</style>
