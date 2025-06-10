<template>
  <div class="system-api-user">
    <bk-alert
      type="info"
      :title="
        $t(
          '仅已授权应用才能访问平台注册在 API 网关上的应用态 API。若需访问非 “基础可读” 级别的 API，除了在 API 网关申请权限外，还需在此处手动为应用添加相应权限。'
        )
      "
    ></bk-alert>
    <div class="top-box flex-row justify-content-between mt16">
      <bk-button
        :theme="'primary'"
        icon="plus"
        @click="showAddDialog('add')"
      >
        {{ $t('添加授权应用') }}
      </bk-button>
      <bk-input
        v-model="pgSearchValue"
        :placeholder="$t('请输入应用 ID，按 Enter 搜索')"
        :right-icon="'bk-icon icon-search'"
        style="width: 400px"
        :clearable="true"
        @input="pgHandleCombinedSearch"
      ></bk-input>
    </div>
    <div class="card-style mt16">
      <bk-table
        :data="pgPaginatedData"
        :pagination="pagination"
        dark-header
        size="small"
        class="plan-table-cls"
        v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
        @page-change="pgHandlePageChange"
        @page-limit-change="pgHandlePageLimitChange"
        @filter-change="handleFilterChange"
      >
        <bk-table-column
          v-for="column in columns"
          v-bind="column"
          :label="column.label"
          :prop="column.prop"
          :key="column.name"
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            <span v-if="column.prop === 'role'">{{ roleMap[row[column.prop]] || '--' }}</span>
            <span v-else>{{ row[column.prop] || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('操作')"
          :width="180"
        >
          <template slot-scope="{ row }">
            <bk-button
              theme="primary"
              class="mr10"
              text
              @click="showAddDialog('edit', row)"
            >
              {{ $t('修改权限') }}
            </bk-button>
            <bk-button
              theme="primary"
              text
              @click="showDeleteDialog(row)"
            >
              {{ $t('删除') }}
            </bk-button>
          </template>
        </bk-table-column>
      </bk-table>
    </div>

    <!-- 添加系统API用户 -->
    <bk-dialog
      v-model="editAddDialogConfig.visible"
      header-position="left"
      theme="primary"
      :width="480"
      :mask-close="false"
      :auto-close="false"
      :title="isAdd ? $t('添加授权应用') : $t('编辑权限')"
      :loading="editAddDialogConfig.loading"
      ext-cls="edit-add-dialog-cls"
      @value-change="handleValueChange"
      @confirm="handleConfirm"
    >
      <div
        slot="header"
        class="edit-add-title"
      >
        {{ isAdd ? $t('添加授权应用') : $t('编辑权限') }}
        <span
          v-if="!isAdd"
          class="sub-title"
        >
          {{ editAddDialogConfig.formData.appId }}
        </span>
      </div>
      <bk-form
        :label-width="200"
        form-type="vertical"
        :model="editAddDialogConfig.formData"
        ref="editAddForm"
      >
        <bk-form-item
          v-if="isAdd"
          :label="$t('应用 ID')"
          :required="true"
          :property="'appId'"
          :rules="isAdd ? requiredRule : []"
          :error-display-type="'normal'"
        >
          <bk-input
            v-model="editAddDialogConfig.formData.appId"
            :disabled="!isAdd"
          ></bk-input>
        </bk-form-item>
        <bk-form-item
          :label="$t('权限')"
          :required="true"
          :property="'role'"
          :rules="requiredRule"
          :error-display-type="'normal'"
        >
          <bk-select v-model="editAddDialogConfig.formData.role">
            <bk-option
              v-for="option in roleList"
              :key="option.value"
              :id="option.value"
              :name="option.label"
            ></bk-option>
          </bk-select>
        </bk-form-item>
      </bk-form>
    </bk-dialog>

    <!-- 删除 -->
    <DeleteDialog
      :show.sync="deleteDialogConfig.visible"
      :title="$t('确认删除已授权应用')"
      :expected-confirm-text="deleteDialogConfig.rowName"
      :loading="deleteDialogConfig.isLoading"
      @confirm="deleteSystemApiUser"
    >
      <div class="hint-text">{{ $t('删除后将不能再调用平台提供的系统 API') }}</div>
      <div class="hint-text">
        <span>{{ $t('该操作不可撤销，请输入应用 ID') }}</span>
        <span>
          （
          <span class="sign">{{ deleteDialogConfig.rowName }}</span>
          <i
            class="paasng-icon paasng-general-copy"
            v-copy="deleteDialogConfig.rowName"
          />
          ）
        </span>
        {{ $t('进行确认') }}
      </div>
    </DeleteDialog>
  </div>
</template>

<script>
import paginationMixin from '../pagination-mixin.js';
import DeleteDialog from '@/components/delete-dialog';
import { mapState } from 'vuex';

export default {
  name: 'UserFeature',
  // 分页逻辑使用mixins导入
  mixins: [paginationMixin],
  components: {
    DeleteDialog,
  },
  data() {
    return {
      // api用户列表
      systemApiUserList: [],
      isTableLoading: true,
      // 新建编辑弹窗配置
      editAddDialogConfig: {
        visible: false,
        loading: false,
        type: 'add',
        row: {},
        formData: {
          // tenant/any
          method: 'tenant',
          appId: '',
          role: '',
        },
      },
      deleteDialogConfig: {
        visible: false,
        isLoading: false,
        rowName: '',
      },
      // 权限
      roleList: [],
      requiredRule: [
        {
          required: true,
          message: this.$t('必填项'),
          trigger: 'blur',
        },
      ],
    };
  },
  computed: {
    ...mapState({
      platformFeature: (state) => state.platformFeature,
    }),
    // 权限对应映射关系
    roleMap() {
      return this.roleList.reduce((acc, item) => {
        acc[item.value] = item.label;
        return acc;
      }, {});
    },
    isAdd() {
      return this.editAddDialogConfig.type === 'add';
    },
    columns() {
      return [
        {
          label: this.$t('应用 ID'),
          prop: 'bk_app_code',
        },
        {
          label: this.$t('权限'),
          prop: 'role',
          columnKey: 'role',
          filters: this.roleList,
          filterMultiple: false,
        },
        {
          label: this.$t('操作时间'),
          prop: 'updated',
          sortable: true,
        },
      ];
    },
  },
  created() {
    Promise.all([this.getSysapiClient(), this.getSystemApiRoles()]);
  },
  methods: {
    // 表格筛选
    handleFilterChange(filds) {
      if (filds.role) {
        this.pgFieldFilter.filterField = 'role';
        this.pgFieldFilter.filterValue = filds.role.length ? filds.role[0] : null;
      }
      this.pgHandleCombinedSearch();
    },
    // 自定义的过滤函数，提供给mixins中使用
    pgFilterFn(item, keyword) {
      return item.bk_app_code.toLowerCase().includes(keyword);
    },
    // 获取已授权用户
    async getSysapiClient() {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('tenant/getSysapiClient');
        this.systemApiUserList = res;
        // mixins-初始化过滤数据
        this.pgInitPaginationData(res);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        setTimeout(() => {
          this.isTableLoading = false;
        }, 100);
      }
    },
    // 获取系统API权限列表
    async getSystemApiRoles() {
      try {
        const res = await this.$store.dispatch('tenant/getSystemApiRoles');
        this.roleList = res.map((v) => {
          return {
            text: v.label,
            ...v,
          };
        });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    setDialogFormData(appId = '', role = '') {
      this.editAddDialogConfig.formData.appId = appId;
      this.editAddDialogConfig.formData.role = role;
    },
    // 添加系统API用户
    showAddDialog(type, row) {
      this.editAddDialogConfig.visible = true;
      this.editAddDialogConfig.type = type;
      if (type === 'edit') {
        this.setDialogFormData(row.bk_app_code || '--', row.role);
      } else {
        this.setDialogFormData();
      }
    },
    showDeleteDialog(row) {
      this.deleteDialogConfig.visible = true;
      this.deleteDialogConfig.rowName = row.bk_app_code;
    },
    handleConfirm() {
      this.$refs.editAddForm.validate().then(
        () => {
          const { appId, role } = this.editAddDialogConfig.formData;
          const params = {
            bk_app_code: appId,
            role,
          };
          console.log('this', params);
          this.addSystemApiUser(params);
        },
        (validator) => {
          console.error(validator);
        }
      );
    },
    async addSystemApiUser(data) {
      this.editAddDialogConfig.loading = true;
      const dispatchName = this.isAdd ? 'addSystemApiUser' : 'updateSystemApiUser';
      try {
        await this.$store.dispatch(`tenant/${dispatchName}`, {
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.isAdd ? this.$t('添加成功') : this.$t('修改成功'),
        });
        this.editAddDialogConfig.visible = false;
        this.getSysapiClient();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.editAddDialogConfig.loading = false;
      }
    },
    // 关闭删除弹窗
    closeDelDialog() {
      this.deleteDialogConfig.visible = false;
    },
    // 删除系统API用户权限
    async deleteSystemApiUser() {
      this.deleteDialogConfig.isLoading = true;
      try {
        await this.$store.dispatch('tenant/deleteSystemApiUser', {
          name: this.deleteDialogConfig.rowName,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除成功'),
        });
        this.closeDelDialog();
        this.getSysapiClient();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.deleteDialogConfig.isLoading = false;
      }
    },
    // 清除错误提示
    handleValueChange(flag) {
      if (!flag) {
        this.$refs?.editAddForm?.clearError();
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.system-api-user {
  .mt16 {
    margin-top: 16px;
  }
  .card-style {
    padding: 16px;
  }
  /deep/ .bk-table-header .custom-header-cell {
    color: inherit;
    text-decoration: underline;
    text-decoration-style: dashed;
    text-underline-position: under;
  }
}
/deep/ .edit-add-dialog-cls {
  .edit-add-title {
    color: #313238;
    .sub-title {
      display: inline-block;
      line-height: 18px;
      margin-left: 10px;
      padding-left: 8px;
      font-size: 14px;
      color: #979ba5;
      border-left: 1px solid #dcdee5;
    }
  }
}
</style>
