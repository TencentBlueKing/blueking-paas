<template>
  <div class="platform-admin">
    <div class="top-box flex-row justify-content-between">
      <bk-button
        :theme="'primary'"
        icon="plus"
        @click="showAddDialog"
      >
        {{ $t('添加平台管理员') }}
      </bk-button>
      <bk-input
        v-model="pgSearchValue"
        :placeholder="$t('请输入用户 ID 或用户名')"
        :right-icon="'bk-icon icon-search'"
        style="width: 400px"
        :clearable="true"
        @input="pgHandleCombinedSearch"
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
              v-if="column.userDisplay && platformFeature.MULTI_TENANT_MODE"
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
          :label="$t('用户')"
          :required="true"
        >
          <!-- 多租户人员选择器 -->
          <user
            v-model="addAdminDialog.formData.userList"
            :placeholder="$t('请输入用户')"
            :multiple="true"
            :empty-text="$t('无匹配人员')"
          />
        </bk-form-item>
      </bk-form>
    </bk-dialog>

    <!-- 删除 -->
    <delete-dialog
      :show.sync="deleteDialogConfig.visible"
      :title="$t('确认删除平台管理员')"
      :expected-confirm-text="deleteDialogConfig.input"
      :loading="deleteDialogConfig.isLoading"
      :placeholder="$t('请输入用户名确认')"
      @confirm="deletePlatformAdministrator"
    >
      <div class="hint-text">
        <span>{{ $t('删除后将无法再使用平台管理的相关功能。请输入用户 ID') }}</span>
        <span>
          （
          <span class="sign">{{ deleteDialogConfig.input }}</span>
          <i
            class="paasng-icon paasng-general-copy"
            v-copy="deleteDialogConfig.input"
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
import User from '@/components/user';
import { mapState } from 'vuex';
export default {
  name: 'UserFeature',
  // 分页逻辑使用mixins导入
  mixins: [paginationMixin],
  components: {
    User,
    deleteDialog,
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
      },
      columns: [
        {
          label: this.$t('用户 ID'),
          prop: 'user',
        },
        {
          label: this.$t('用户'),
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
      ],
    };
  },
  computed: {
    ...mapState({
      platformFeature: (state) => state.platformFeature,
    }),
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
    },
    handleConfirm() {
      const { userList } = this.addAdminDialog.formData;
      const params = {
        users: userList,
      };
      this.addPlatformAdministrators(params);
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
  },
};
</script>

<style lang="scss" scoped>
.platform-admin {
  .card-style {
    margin-top: 16px;
    padding: 16px;
  }
}
</style>
