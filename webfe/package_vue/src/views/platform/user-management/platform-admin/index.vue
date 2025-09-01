<template>
  <div class="platform-admin">
    <bk-alert
      type="info"
      :title="$t('管理员能查看并执行 “平台管理” 导航下所有操作。')"
    ></bk-alert>
    <div class="top-box flex-row justify-content-between">
      <bk-button
        :theme="'primary'"
        icon="plus"
        @click="showAddDialog"
      >
        {{ $t('添加平台管理员') }}
      </bk-button>
      <user
        v-model="userSearchValues"
        style="width: 400px"
        :multiple="false"
        :placeholder="$t('按用户搜索')"
        :empty-text="$t('无匹配人员')"
      />
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
              v-if="column.userDisplay && isMultiTenantDisplayMode"
              :user-id="row[column.prop]"
            ></bk-user-display-name>
            <span v-else>{{ row[column.prop] ?? '--' }}</span>
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
              @click="handleDelete(row)"
            >
              {{ $t('删除') }}
            </bk-button>
          </template>
        </bk-table-column>
      </bk-table>
    </div>

    <!-- 添加管理员 -->
    <bk-dialog
      v-model="addAdminDialog.visible"
      header-position="left"
      theme="primary"
      :width="480"
      :mask-close="false"
      :title="$t('添加平台管理员')"
      :auto-close="false"
      :loading="addAdminDialog.loading"
      @confirm="handleConfirm"
    >
      <bk-form
        ref="dialogForm"
        :label-width="200"
        form-type="vertical"
        :model="addAdminDialog.formData"
      >
        <bk-form-item
          :label="$t('管理员')"
          :required="true"
          :property="'userList'"
          :rules="userRule"
          :error-display-type="'normal'"
        >
          <!-- 多租户人员选择器 -->
          <user
            v-model="addAdminDialog.formData.userList"
            :placeholder="$t('请输入')"
            :multiple="true"
            :empty-text="$t('无匹配人员')"
            @change="handleUserChange"
          />
        </bk-form-item>
      </bk-form>
    </bk-dialog>

    <!-- 删除 -->
    <bk-dialog
      v-model="deleteDialogConfig.visible"
      theme="primary"
      :width="480"
      :loading="deleteDialogConfig.isLoading"
      :mask-close="false"
      header-position="left"
      :title="$t('确认删除平台管理员')"
      @confirm="deletePlatformAdministrator"
    >
      <span>{{ $t('删除后') }}，</span>
      <bk-user-display-name
        v-if="isMultiTenantDisplayMode"
        :user-id="deleteDialogConfig.user"
      ></bk-user-display-name>
      <span v-else>{{ deleteDialogConfig.user }}</span>
      &nbsp;
      {{ $t('将无法再使用平台管理相关功能。') }}
    </bk-dialog>
  </div>
</template>

<script>
import paginationMixin from '../pagination-mixin.js';
import User from '@/components/user';
import { mapGetters } from 'vuex';
export default {
  name: 'UserFeature',
  // 分页逻辑使用mixins导入
  mixins: [paginationMixin],
  components: {
    User,
  },
  data() {
    return {
      isTableLoading: false,
      addAdminDialog: {
        visible: false,
        loading: false,
        formData: {
          users: '',
          userList: [],
        },
      },
      deleteDialogConfig: {
        visible: false,
        input: '',
        isLoading: false,
        user: '',
      },
      userRule: [
        {
          validator: () => {
            return !!this.addAdminDialog.formData?.userList?.length;
          },
          message: this.$t('必填项'),
          trigger: 'blur',
        },
      ],
      userSearchValues: [],
    };
  },
  computed: {
    ...mapGetters(['tenantId', 'isMultiTenantDisplayMode']),
    columns() {
      const baseColumns = [
        {
          label: `${this.$t('管理员')} ID`,
          prop: 'user',
        },
        {
          label: this.$t('管理员名称'),
          prop: 'user',
          userDisplay: true,
        },
        {
          label: this.$t('所属租户'),
          prop: 'tenant_id',
        },
        {
          label: this.$t('添加时间'),
          prop: 'created',
          sortable: true,
        },
      ];

      if (!this.isMultiTenantDisplayMode) {
        return baseColumns.filter((column) => column.label !== this.$t('管理员名称'));
      }
      return baseColumns;
    },
  },
  watch: {
    userSearchValues(newVal) {
      // 分页搜索
      this.pgSearchValue = newVal.join();
      this.pgHandleCombinedSearch();
    },
  },
  created() {
    this.getAdminUser();
  },
  methods: {
    // 自定义的过滤函数，提供给mixins中使用
    pgFilterFn(item, keyword) {
      return item.user.toLowerCase().includes(keyword);
    },
    // 获取平台管理员
    async getAdminUser() {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('tenant/getAdminUser');
        // mixin-初始化分页数据
        this.pgInitPaginationData(res);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isTableLoading = false;
      }
    },
    // 添加管理员
    showAddDialog() {
      this.addAdminDialog.visible = true;
      this.addAdminDialog.formData.userList = [];
    },
    handleDelete(row) {
      this.deleteDialogConfig.visible = true;
      this.deleteDialogConfig.input = row.user;
      this.deleteDialogConfig.user = row.user;
    },
    async handleConfirm() {
      try {
        await this.$refs.dialogForm.validate();
        const { userList } = this.addAdminDialog.formData;
        const params = userList.map((v) => {
          return {
            user: v,
            tenant_id: this.tenantId,
          };
        });
        this.addPlatformAdministrators(params);
      } catch (error) {
        console.error('Form validation failed:', error);
      }
    },
    // 添加平台管理员
    async addPlatformAdministrators(data) {
      this.addAdminDialog.loading = true;
      try {
        await this.$store.dispatch('tenant/addPlatformAdministrators', {
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('添加成功'),
        });
        this.addAdminDialog.visible = false;
        this.getAdminUser();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.addAdminDialog.loading = false;
      }
    },
    // 删除平台管理员
    async deletePlatformAdministrator() {
      this.deleteDialogConfig.isLoading = true;
      try {
        await this.$store.dispatch('tenant/deletePlatformAdministrator', {
          id: this.deleteDialogConfig.input,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除成功'),
        });
        this.deleteDialogConfig.visible = false;
        this.getAdminUser();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.deleteDialogConfig.isLoading = false;
      }
    },
    handleUserChange() {
      this.$refs.dialogForm.validateField('userList').catch((e) => {
        console.error(e);
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.platform-admin {
  .top-box {
    margin-top: 16px;
  }
  .card-style {
    margin-top: 16px;
    padding: 16px;
  }
}
</style>
