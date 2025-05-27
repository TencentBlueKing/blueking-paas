<template>
  <div class="palt-app-service-container">
    <div class="top-box">
      <bk-alert
        type="info"
        class="recycle-alert-cls"
        closable
      >
        <div slot="title">
          <span>
            {{
              $t('您有 {n} 个已解绑但未回收的增强服务实例，未回收的实例仍会计入应用成本，请及时回收。', {
                n: unboundServices?.length,
              })
            }}
          </span>
          <bk-button
            text
            size="small"
          >
            {{ $t('立即回收') }}
          </bk-button>
        </div>
      </bk-alert>
      <bk-input
        v-model="searchValue"
        :placeholder="$t('请输入模块名称')"
        :right-icon="'bk-icon icon-search'"
        style="width: 400px"
        clearable
      ></bk-input>
    </div>
    <bk-table
      :data="serviceList"
      ref="tableRef"
      size="small"
      class="service-table-cls"
      col-border
      :span-method="objectSpanMethod"
      v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
      :cell-class-name="cellClassName"
    >
      <bk-table-column
        :label="$t('模块')"
        prop="moduleName"
        show-overflow-tooltip
      />
      <bk-table-column
        :label="$t('增强服务')"
        show-overflow-tooltip
      >
        <template slot-scope="{ row }">
          <span>{{ row.service.display_name }}</span>
          <span
            v-if="row.sharedTag"
            class="shared"
            v-bk-tooltips="$t('共享 {m} 模块', { m: row?.ref_module?.name })"
          >
            {{ $t('共享') }}
          </span>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('配置信息')"
        show-overflow-tooltip
      >
        <template slot-scope="{ row }">
          <div
            v-if="row.plans"
            class="config-info-tag"
          >
            <span
              class="border-tag text-ellipsis"
              v-if="row.plans?.stag?.name === row.plans?.prod?.name"
              v-bk-overflow-tips
            >
              {{ row.plans.stag?.name }}
            </span>
            <span
              v-else
              v-for="(value, key) in row.plans"
              class="border-tag text-ellipsis"
              :key="key"
              v-bk-overflow-tips
            >
              {{ getEnvironmentName(key) }}：{{ value.name }}
            </span>
          </div>
          <span v-else>--</span>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('环境')"
        :width="140"
        column-key="environment"
        show-overflow-tooltip
      >
        <template slot-scope="{ row }">
          {{ envMap[row.env] }}
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('是否分配实例')"
        :width="120"
      >
        <template slot-scope="{ row }">
          {{ row.envInfos?.is_provisioned ? $t('是') : $t('否') }}
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('操作')"
        :width="240"
      >
        <template slot-scope="{ row }">
          <!-- instance_uuid 实例id为空允许分配实例 -->
          <span
            class="mr10"
            v-bk-tooltips="{
              content: $t('实例已分配'),
              disabled: !row.envInfos?.instance_uuid,
            }"
          >
            <bk-button
              text
              :disabled="!!row.envInfos?.instance_uuid"
              @click="showAssignInstanceDialog(row)"
            >
              {{ $t('分配实例') }}
            </bk-button>
          </span>
          <span
            class="mr10"
            v-bk-tooltips="{
              content: $t('未分配实例无法删除'),
              disabled: !!row.envInfos?.instance_uuid,
            }"
          >
            <!-- instance_uuid： null 未绑定服务实例 -->
            <bk-button
              text
              :disabled="!row.envInfos?.instance_uuid"
              @click="showDeleteDialog(row)"
            >
              {{ $t('删除实例') }}
            </bk-button>
          </span>
          <!-- provision_infos[env].instance_uuid 为 null 未分配实例，不能查看 -->
          <bk-button
            text
            :disabled="!row.envInfos?.instance_uuid"
            @click="viewCredentials(row)"
          >
            {{ $t('查看凭证') }}
          </bk-button>
        </template>
      </bk-table-column>
    </bk-table>

    <!-- 分配实例 -->
    <assign-instance-dialog
      :show.sync="instanceDialogConfig.visible"
      :data="instanceDialogConfig.row"
      :loading="instanceDialogConfig.loading"
      @confirm="assignEnhancedServiceInstance"
    />

    <!-- 查看凭证 -->
    <EditorSideslider
      :show.sync="credentialConfig.visible"
      :title="$t('凭证信息')"
      :sub-title="subTitle"
      :value="valuesJson"
      :read-only="true"
    />

    <!-- 删除实例 -->
    <DeleteDialog
      :show.sync="deleteDialogConfig.visible"
      :title="$t('确认删除实例')"
      :expected-confirm-text="appCode"
      :loading="deleteDialogConfig.isLoading"
      @confirm="unassignServiceInstance"
    >
      <div class="hint-text">
        {{
          $t('确认删除 {m} 模块的{e} {n} 增强服务实例', {
            m: deleteDialogConfig.row?.moduleName,
            e: envMap[deleteDialogConfig.row?.env],
            n: deleteDialogConfig.row?.service?.display_name,
          })
        }}
      </div>
      <div class="hint-text mt8">
        <span>{{ $t('该操作不可撤销，请输入应用 ID') }}</span>
        <span>
          （
          <span class="sign">{{ appCode }}</span>
          <i
            class="paasng-icon paasng-general-copy"
            v-copy="appCode"
          />
          ）
        </span>
        {{ $t('进行确认') }}
      </div>
    </DeleteDialog>
  </div>
</template>

<script>
import assignInstanceDialog from './assign-instance-dialog.vue';
import EditorSideslider from '@/components/editor-sideslider';
import DeleteDialog from '@/components/delete-dialog';

export default {
  components: {
    assignInstanceDialog,
    EditorSideslider,
    DeleteDialog,
  },
  data() {
    return {
      searchValue: '',
      serviceList: [],
      isTableLoading: false,
      // 分配实例
      instanceDialogConfig: {
        visible: false,
        row: {},
        loading: false,
      },
      // 凭证侧栏信息
      credentialConfig: {
        visible: false,
        row: {},
        data: {},
      },
      // 删除实例
      deleteDialogConfig: {
        visible: false,
        isLoading: false,
        rowName: '',
        row: {},
      },
      // 未绑定服务实例
      unboundServices: [],
      envMap: {
        stag: this.$t('预发布环境'),
        prod: this.$t('生产环境'),
      },
    };
  },
  computed: {
    appCode() {
      return this.$route.params.code;
    },
    valuesJson() {
      return JSON.stringify(this.credentialConfig.data, null, 2);
    },
    subTitle() {
      const { service, moduleName, env } = this.credentialConfig.row;
      return `${moduleName}模块 / ${this.envMap[env]} / ${service?.display_name}增强服务`;
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.getServices();
      this.getUnboundAttachments();
    },
    // 合并单元格
    objectSpanMethod({ row, column, rowIndex, columnIndex }) {
      const defaultSpan = { rowspan: 0, colspan: 0 };
      // 模块
      if (columnIndex === 0) {
        return row.mergeCellTag
          ? {
              rowspan: row.mergeCellTag * 2,
              colspan: 1,
            }
          : defaultSpan;
      }
      // 增强服务、配置信息
      if (columnIndex === 1 || columnIndex === 2) {
        return rowIndex % 2 === 0
          ? {
              rowspan: 2,
              colspan: 1,
            }
          : defaultSpan;
      }
    },
    cellClassName({ column }) {
      return column.columnKey === 'environment' ? 'environment-cell-cls' : '';
    },
    getEnvironmentName(key) {
      return key === 'prod' ? this.$t('方案（生产环境）') : this.$t('方案（预发布环境）');
    },
    // 获取增强服务数据
    async getServices() {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('tenantOperations/getBoundServices', {
          appCode: this.appCode,
        });
        this.serviceList = res.flatMap((item) => {
          // shared_services 共享服务
          const sharedServices = item.shared_services.map((service) => ({
            ...service,
            sharedTag: true,
          }));
          // bound_services 绑定服务
          const boundServices = item.bound_services;
          // 当前模块下的所有服务
          const allServices = [...boundServices, ...sharedServices];

          return allServices.flatMap((service, index) => [
            {
              ...service,
              moduleName: item.module_name,
              env: 'stag',
              mergeCellTag: index === 0 ? allServices.length : 0,
              // 实例是否分配
              envInfos: service.provision_infos?.find((v) => v.env_name === 'stag') || {},
            },
            {
              ...service,
              moduleName: item.module_name,
              env: 'prod',
              mergeCellTag: 0,
              // 实例是否分配
              envInfos: service.provision_infos?.find((v) => v.env_name === 'prod') || {},
            },
          ]);
        });
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isTableLoading = false;
      }
    },
    // 显示分配实例弹窗
    showAssignInstanceDialog(row) {
      this.toggleInstanceAssignmentDialog(true);
      this.instanceDialogConfig.row = row;
    },
    /**
     * 控制实例分配对话框的显示状态
     * @param {boolean} [visible=false] - 对话框的显示状态，默认为关闭
     */
    toggleInstanceAssignmentDialog(visible = false) {
      this.instanceDialogConfig.visible = visible;
    },
    // 分配增强服务实例
    async assignEnhancedServiceInstance() {
      this.instanceDialogConfig.loading = true;
      const { service, moduleName, env } = this.instanceDialogConfig.row;
      try {
        await this.$store.dispatch('tenantOperations/assignEnhancedServiceInstance', {
          appCode: this.appCode,
          moduleId: moduleName,
          env: env,
          serviceId: service?.uuid,
        });
        this.getServices();
        this.toggleInstanceAssignmentDialog();
        this.$paasMessage({
          theme: 'success',
          message: this.$t('分配成功'),
        });
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        setTimeout(() => {
          this.instanceDialogConfig.loading = false;
        }, 1000);
      }
    },
    // 删除实例弹窗
    showDeleteDialog(row) {
      this.deleteDialogConfig.row = row;
      this.toggleDelDialog(true);
    },
    // 关闭删除弹窗
    toggleDelDialog(visible = false) {
      this.deleteDialogConfig.visible = visible;
    },
    // 解绑服务实例
    async unassignServiceInstance() {
      try {
        const { service, moduleName, env, envInfos } = this.deleteDialogConfig.row;
        await this.$store.dispatch('tenantOperations/unassignServiceInstance', {
          appCode: this.appCode,
          moduleId: moduleName,
          env: env,
          serviceId: service?.uuid,
          instanceId: envInfos?.instance_uuid,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除成功'),
        });
        this.init();
        this.toggleDelDialog(false);
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 查看凭证
    viewCredentials(row) {
      this.getCredentials(row);
      this.credentialConfig.visible = true;
      this.credentialConfig.row = row;
    },
    // 获取增服务实例凭证
    async getCredentials(row) {
      try {
        const { service, moduleName, env, envInfos } = row;
        const ret = await this.$store.dispatch('tenantOperations/getCredentials', {
          appCode: this.appCode,
          moduleId: moduleName,
          env: env,
          serviceId: service?.uuid,
          instanceId: envInfos?.instance_uuid,
        });
        this.credentialConfig.data = ret;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取未绑定增强服务实例（未回收）
    async getUnboundAttachments() {
      try {
        const res = await this.$store.dispatch('tenantOperations/getUnboundAttachments', {
          appCode: this.appCode,
        });
        this.unboundServices = res;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.mt8 {
  margin-top: 8px;
}
.palt-app-service-container {
  .top-box {
    margin-bottom: 16px;
  }
  .recycle-alert-cls {
    margin-bottom: 16px;
    .bk-button-text {
      line-height: 1 !important;
      height: 12px !important;
      padding: 0;
    }
  }
  .service-table-cls {
    /deep/ .environment-cell-cls {
      .cell {
        padding: 0 15px;
      }
    }
    .shared {
      display: inline-block;
      margin-left: 5px;
      height: 16px;
      line-height: 16px;
      padding: 0 4px;
      font-size: 10px;
      color: #1768ef;
      background: #e1ecff;
      border-radius: 8px;
    }
    .config-info-tag {
      display: flex;
      flex-direction: column;
      flex-wrap: wrap;
      gap: 4px;
      padding: 10px 0;
      .border-tag {
        max-width: 100%;
        width: fit-content;
        margin: 0px;
        border-radius: 12px;
      }
    }
  }
}
</style>
