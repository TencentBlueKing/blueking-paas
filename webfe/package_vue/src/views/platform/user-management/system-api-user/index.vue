<template>
  <div class="system-api-user">
    <div class="top-box flex-row justify-content-between">
      <bk-button
        :theme="'primary'"
        icon="plus"
        @click="showAddDialog('add')"
      >
        {{ $t('添加系统 API 用户') }}
      </bk-button>
      <bk-input
        v-model="pgSearchValue"
        :placeholder="$t('请输入应用 ID')"
        :right-icon="'bk-icon icon-search'"
        style="width: 400px"
        @input="pgHandleSearch"
      ></bk-input>
    </div>
    <div class="card-style">
      <bk-table
        :data="pgPaginatedData"
        :pagination="pagination"
        dark-header
        size="small"
        class="plan-table-cls"
        v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
        @page-change="pgHandlePageChange"
        @page-limit-change="pgHandlePageLimitChange"
      >
        <bk-table-column
          v-for="column in columns"
          v-bind="column"
          :label="column.label"
          :prop="column.prop"
          :key="column.user"
          show-overflow-tooltip
        >
          <template slot-scope="{ row }">
            <bk-user-display-name
              v-if="column.prop === 'user' && platformFeature.MULTI_TENANT_MODE"
              :user-id="row[column.prop]"
            ></bk-user-display-name>
            <span v-else-if="column.prop === 'role'">{{ roleMap[row[column.prop]] || '--' }}</span>
            <span v-else>{{ row[column.prop] || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('操作')"
          :width="160"
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
      :title="isAdd ? $t('添加系统 API 用户') : $t('编辑权限')"
      :loading="editAddDialogConfig.loading"
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
              :key="option.id"
              :id="option.id"
              :name="option.name"
            ></bk-option>
          </bk-select>
        </bk-form-item>
      </bk-form>
    </bk-dialog>

    <!-- 删除 -->
    <delete-dialog
      :show.sync="deleteDialogConfig.visible"
      :title="$t('确认删除系统 API 用户')"
      :expected-confirm-text="deleteDialogConfig.rowUser"
      :loading="deleteDialogConfig.isLoading"
      :placeholder="$t('请输入用户名确认')"
      @confirm="deleteSystemApiUser"
    >
      <div class="hint-text">{{ $t('删除后将不能再调用平台提供的系统 API') }}</div>
      <div class="hint-text">
        <span>{{ $t('该操作不可撤销，请输入用户名') }}</span>
        <span>
          （
          <span class="sign">{{ deleteDialogConfig.rowUser }}</span>
          <i
            class="paasng-icon paasng-general-copy"
            v-copy="deleteDialogConfig.rowUser"
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
      isTableLoading: false,
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
        rowUser: '',
      },
      columns: [
        {
          label: this.$t('用户'),
          prop: 'user',
        },
        {
          label: this.$t('应用 ID'),
          prop: 'bk_app_code',
        },
        {
          label: this.$t('权限'),
          prop: 'role',
        },
        {
          label: this.$t('操作时间'),
          prop: 'updated',
          sortable: true,
        },
      ],
      // 权限对应映射关系
      roleMap: {
        1: this.$t('没有特定角色'),
        50: this.$t('基础可读'),
        60: this.$t('基础管理'),
        70: this.$t('轻应用管理'),
        80: this.$t('lesscode 系统专用角色'),
      },
      requiredRule: [
        {
          required: true,
          message: this.$t('请输入'),
          trigger: 'blur',
        },
      ],
    };
  },
  computed: {
    ...mapState({
      platformFeature: (state) => state.platformFeature,
    }),
    roleList() {
      return Object.entries(this.roleMap).map(([id, name]) => ({
        id: Number(id),
        name,
      }));
    },
    isAdd() {
      return this.editAddDialogConfig.type === 'add';
    },
  },
  created() {
    this.getSystemApiUser();
  },
  methods: {
    // 自定义的过滤函数，提供给mixins中使用
    pgFilterFn(item, keyword) {
      return item.user.toLowerCase().includes(keyword);
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
        this.isTableLoading = false;
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
      this.deleteDialogConfig.rowUser = row.user;
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
          user: this.deleteDialogConfig.rowUser,
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
  .card-style {
    margin-top: 16px;
    padding: 16px;
  }
}
</style>
