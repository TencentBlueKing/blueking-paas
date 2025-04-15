<template>
  <div class="platform-admin">
    <div class="top-box flex-row justify-content-between">
      <bk-button
        :theme="'primary'"
        icon="plus"
        @click="addAdmin"
      >
        {{ $t('添加平台管理员') }}
      </bk-button>
      <bk-input
        v-model="pgSearchValue"
        :placeholder="$t('请输入用户 ID 或用户名')"
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
            {{ row[column.prop] || '--' }}
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
    >
      <bk-form
        :label-width="200"
        form-type="vertical"
        :model="addAdminDialog.formData"
        ref="validateForm1"
      >
        <bk-form-item
          :label="$t('添加方式')"
          :required="true"
        >
          <bk-radio-group
            v-model="addAdminDialog.formData.method"
            style="margin-bottom: 10px"
          >
            <bk-radio :value="'tenant'">{{ $t('添加当前租户下的用户') }}</bk-radio>
            <bk-radio :value="'any'">{{ $t('添加任意用户') }}</bk-radio>
          </bk-radio-group>
          <!-- 多租户人员选择器 -->
          <bk-input
            v-model="addAdminDialog.formData.users"
            :placeholder="$t('请输入用户ID')"
          ></bk-input>
        </bk-form-item>
      </bk-form>
    </bk-dialog>
  </div>
</template>

<script>
import paginationMixin from '../pagination-mixin.js';
export default {
  name: 'UserFeature',
  // 分页逻辑使用mixins导入
  mixins: [paginationMixin],
  data() {
    return {
      isTableLoading: false,
      addAdminDialog: {
        visible: false,
        formData: {
          // tenant/any
          method: 'tenant',
          users: '',
        },
      },
      columns: [
        {
          label: this.$t('用户'),
          prop: 'user',
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
    addAdmin() {
      this.addAdminDialog.visible = true;
    },
    handleDelete() {},
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
