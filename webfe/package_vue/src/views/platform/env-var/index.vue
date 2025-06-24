<template>
  <div class="right-main builtIn-env-variable-container">
    <bk-alert
      type="info"
      :title="
        $t(
          '此处定义的环境变量会覆盖系统内置的环境变量。环境变量优先级（由高到低）：平台管理自定义的内置环境变量 > 系统内置环境变量 > 单个应用中自定义环境变量'
        )
      "
    ></bk-alert>
    <div class="top-box">
      <bk-button
        :theme="'primary'"
        class="mr10"
        icon="plus"
        @click="handleShowAddDialog"
      >
        {{ $t('内置环境变量') }}
      </bk-button>
    </div>
    <bk-table
      ref="tableRef"
      :data="varList"
      size="small"
      class="plan-table-cls"
      v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
    >
      <bk-table-column
        v-for="column in columns"
        v-bind="column"
        :label="$t(column.label)"
        :prop="column.prop"
        :key="column.prop"
        show-overflow-tooltip
      >
        <template slot-scope="{ row }">
          <span v-if="column.prop === 'key'">{{ `${prefix}${row[column.prop]}` || '--' }}</span>
          <bk-user-display-name
            v-else-if="column.prop === 'operator' && platformFeature.MULTI_TENANT_MODE"
            :user-id="row[column.prop]"
          ></bk-user-display-name>
          <span v-else>{{ row[column.prop] || '--' }}</span>
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
            @click="handleEditVar(row)"
          >
            {{ $t('编辑') }}
          </bk-button>
          <bk-button
            theme="primary"
            text
            @click="handleDeleteVar(row)"
          >
            {{ $t('删除') }}
          </bk-button>
        </template>
      </bk-table-column>
    </bk-table>

    <!-- 添加、编辑内置环境变量 -->
    <bk-dialog
      v-model="varDialogConfig.visible"
      width="480"
      theme="primary"
      :mask-close="false"
      :auto-close="false"
      header-position="left"
      :title="isEditVar ? $t('编辑内置环境变量') : $t('添加内置环境变量')"
      :loading="varDialogConfig.loading"
      @after-leave="reset"
      @confirm="handleAddConfirm"
    >
      <bk-form
        :label-width="75"
        :model="dialogFormData"
        :rules="rules"
        ref="addForm"
      >
        <bk-form-item
          label="Key"
          :required="true"
          :property="'key'"
          :error-display-type="'normal'"
        >
          <bk-input
            v-model="dialogFormData.key"
            :disabled="isEditVar"
          >
            <template slot="prepend">
              <div
                class="group-text"
                style="line-height: 32px"
              >
                {{ prefix }}
              </div>
            </template>
          </bk-input>
        </bk-form-item>
        <bk-form-item
          label="Value"
          :required="true"
          :property="'value'"
          :error-display-type="'normal'"
        >
          <bk-input v-model="dialogFormData.value"></bk-input>
        </bk-form-item>
        <bk-form-item
          :label="$t('描述')"
          :required="true"
          :property="'description'"
          :error-display-type="'normal'"
        >
          <bk-input v-model="dialogFormData.description"></bk-input>
        </bk-form-item>
      </bk-form>
    </bk-dialog>

    <!-- 删除内置环境变量 -->
    <DeleteDialog
      :show.sync="deleteDialogConfig.visible"
      :title="$t('确认删除内置环境变量')"
      :expected-confirm-text="deletedKey"
      :loading="deleteDialogConfig.loading"
      @confirm="deleteBuiltinConfigVars"
    >
      <div class="hint-text">
        <p>{{ $t('删除后，所有应用在重新部署时将不再下发该环境变量。') }}</p>
        <span>{{ $t('请输入要删除的内置环境变量 key') }}</span>
        <span class="hint-text">
          （
          <span class="sign">{{ deletedKey }}</span>
          <i
            class="paasng-icon paasng-general-copy"
            v-copy="deletedKey"
          />
          ）
        </span>
        {{ $t('进行确认') }}
      </div>
    </DeleteDialog>
  </div>
</template>

<script>
import DeleteDialog from '@/components/delete-dialog';
import { mapState } from 'vuex';

export default {
  name: 'BuiltInEnvVariable',
  components: {
    DeleteDialog,
  },
  data() {
    return {
      varList: [],
      isTableLoading: false,
      prefix: 'BKPAAS_',
      columns: [
        {
          label: 'key',
          prop: 'key',
        },
        {
          label: 'Value',
          prop: 'value',
        },
        {
          label: '描述',
          prop: 'description',
        },
        {
          label: '更新时间',
          prop: 'updated',
          sortable: true,
        },
        {
          label: '更新人',
          prop: 'operator',
        },
      ],
      varDialogConfig: {
        visible: false,
        loading: false,
        type: 'add',
        row: {},
      },
      deleteDialogConfig: {
        visible: false,
        loading: false,
        row: {},
      },
      dialogFormData: {
        key: '',
        value: '',
        description: '',
      },
      rules: {
        key: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
          {
            max: 64,
            message: this.$t('不能超过64个字符'),
            trigger: 'blur',
          },
          {
            regex: /^[A-Z][A-Z0-9_]*$/,
            message: this.$t('只能以大写字母开头，仅包含大写字母、数字与下划线'),
            trigger: 'blur',
          },
        ],
        value: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
          {
            max: 2048,
            message: this.$t('不能超过2048个字符'),
            trigger: 'blur',
          },
        ],
        description: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
          {
            max: 200,
            message: this.$t('不能超过200个字符'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    ...mapState(['platformFeature']),
    isEditVar() {
      return this.varDialogConfig.type === 'edit';
    },
    deletedKey() {
      return `${this.prefix}${this.deleteDialogConfig.row.key}`;
    },
  },
  created() {
    this.getBuiltinConfigVars();
  },
  methods: {
    // 获取内置环境变量列表
    async getBuiltinConfigVars() {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('tenantConfig/getBuiltinConfigVars');
        this.varList = res;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isTableLoading = false;
      }
    },
    // 新建、编辑环境变量
    async builtinConfigVarOperation() {
      try {
        const dispatchName = this.isEditVar ? 'updateBuiltinConfigVars' : 'addBuiltinConfigVars';
        const successMessage = this.isEditVar ? this.$t('修改环境变量成功') : this.$t('添加环境变量成功');
        const payload = {
          params: this.dialogFormData,
          ...(this.isEditVar && { id: this.varDialogConfig.row.id }),
        };
        await this.$store.dispatch(`tenantConfig/${dispatchName}`, payload);
        this.$paasMessage({
          theme: 'success',
          message: successMessage,
        });
        this.toggleVarDialog(false);
        this.getBuiltinConfigVars();
      } catch (error) {
        this.catchErrorHandler(error);
      } finally {
        this.varDialogConfig.loading = false;
      }
    },
    // 删除内置环境变量
    async deleteBuiltinConfigVars() {
      this.deleteDialogConfig.loading = true;
      try {
        await this.$store.dispatch('tenantConfig/deleteBuiltinConfigVars', {
          id: this.deleteDialogConfig.row?.id,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除环境变量成功'),
        });
        this.toggleDeleteDialog(false);
        this.getBuiltinConfigVars();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.deleteDialogConfig.loading = false;
      }
    },
    toggleVarDialog(visible) {
      this.varDialogConfig.visible = visible;
    },
    toggleDeleteDialog(visible) {
      this.deleteDialogConfig.visible = visible;
    },
    // 重置数据
    reset() {
      this.$refs.addForm?.clearError();
      this.dialogFormData = {
        key: '',
        value: '',
        description: '',
      };
    },
    handleAddConfirm() {
      this.$refs.addForm?.validate().then(
        () => {
          this.varDialogConfig.loading = true;
          this.builtinConfigVarOperation();
        },
        (e) => {
          console.error(e);
        }
      );
    },
    // 新建环境变量弹窗
    handleShowAddDialog() {
      this.toggleVarDialog(true);
      this.varDialogConfig.type = 'add';
    },
    // 编辑环境变量
    handleEditVar(row) {
      this.toggleVarDialog(true);
      this.varDialogConfig.type = 'edit';
      this.varDialogConfig.row = row;
      this.dialogFormData = {
        key: row.key,
        value: row.value,
        description: row.description,
      };
    },
    // 删除内置环境变量
    handleDeleteVar(row) {
      this.deleteDialogConfig.row = row;
      this.toggleDeleteDialog(true);
    },
  },
};
</script>

<style lang="scss" scoped>
.builtIn-env-variable-container {
  padding: 24px;
  .top-box {
    margin: 16px 0;
  }
}
</style>
