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
        :label="$t('实例配置')"
        prop="conditions"
      >
        <div slot-scope="{ row }">
          <!-- JSON格式预览 -->
          <vue-json-pretty
            class="paas-vue-json-pretty-cls"
            :data="row.jsonData"
            :deep="Object.keys(row.jsonData)?.length ? 1 : 0"
            :show-length="true"
            :highlight-mouseover-node="true"
          />
        </div>
      </bk-table-column>
      <bk-table-column
        :label="$t('已分配')"
        prop="name"
        :width="100"
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
        :width="100"
      >
        <template slot-scope="{ row }">
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
    <EditAddDilaog
      :show.sync="dialogConfig.isShow"
      :data="dialogConfig"
      @refresh="getPreCreatedInstances"
    />
  </div>
</template>

<script>
import EditAddDilaog from './edit-add-dilaog.vue';
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
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
    VueJsonPretty,
    EditAddDilaog,
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
          return Object.assign(item, { jsonData: JSON.parse(item.credentials) });
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
  },
};
</script>

<style lang="scss" scoped>
.resource-pool-container {
  .resource-pool-cls {
    margin-top: 16px;
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
