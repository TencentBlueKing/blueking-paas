<template>
  <div class="system-api-user">
    <bk-alert
      type="info"
      :title="
        $t(
          '应用需要创建对应的系统 API 账号，才能访问平台注册在 API 网关上的应用态 API。当应用通过 API 网关访问“基础可读”级别的应用态 API 时，平台会自动为该应用添添加账号和权限。若需访问其他权限级别的应用态 API，除了在 API 网关申请权限外，还需在此处创建账号并添加相应权限。'
        )
      "
    ></bk-alert>
    <div class="top-box flex-row justify-content-between mt16">
      <bk-button
        :theme="'primary'"
        icon="plus"
        @click="showAddDialog('add')"
      >
        {{ $t('添加系统 API 账号') }}
      </bk-button>
      <bk-input
        v-model="pgSearchValue"
        :placeholder="$t('请输入应用 ID')"
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
      :title="isAdd ? $t('添加系统 API 账号') : $t('编辑权限')"
      :loading="editAddDialogConfig.loading"
      @value-change="handleValueChange"
      @confirm="handleConfirm"
    >
      <bk-form
        :label-width="200"
        form-type="vertical"
        :model="editAddDialogConfig.formData"
        ref="editAddForm"
      >
        <bk-form-item
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
    <delete-dialog
      :show.sync="deleteDialogConfig.visible"
      :title="$t('确认删除系统 API 账号')"
      :expected-confirm-text="deleteDialogConfig.rowName"
      :loading="deleteDialogConfig.isLoading"
      :placeholder="$t('请输入用户名确认')"
      @confirm="deleteSystemApiUser"
    >
      <div class="hint-text">{{ $t('删除后将不能再调用平台提供的系统 API') }}</div>
      <div class="hint-text">
        <span>{{ $t('该操作不可撤销，请输入用户名') }}</span>
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
    </delete-dialog>
  </div>
</template>

<script>
import paginationMixin from '../pagination-mixin.js';
import deleteDialog from '../components/delete-dialog.vue';
import { mapState } from 'vuex';

export default {
  name: 'UserFeature',
  // 分页逻辑使用mixins导入
  mixins: [paginationMixin],
  components: {
    deleteDialog,
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
          label: this.$t('API 账号'),
          prop: 'name',
          renderHeader: this.renderHeader,
        },
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
    Promise.all([this.getSystemApiUser(), this.getSystemApiRoles()]);
  },
  methods: {
    renderHeader(h, data) {
      const directive = {
        name: 'bkTooltips',
        content: this.$t('平台自动生成用于内部权限校验的账号'),
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
      return item.name.toLowerCase().includes(keyword);
    },
    // 获取系统API用户列表
    async getSystemApiUser() {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('tenant/getSystemApiUser');
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
      this.deleteDialogConfig.rowName = row.name;
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
        this.getSystemApiUser();
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
        this.getSystemApiUser();
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
.custom-dialog-cls {
  .hint-text {
    font-size: 14px;
    color: #4d4f56;
    letter-spacing: 0;
    line-height: 22px;
    margin-bottom: 8px;
  }
  .sign {
    color: #ea3636;
  }
  .paasng-general-copy {
    margin-left: 3px;
    color: #3a84ff;
    cursor: pointer;
  }
}
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
</style>
