<template>
  <div class="system-api-user">
    <div class="top-box flex-row justify-content-between">
      <bk-button
        :theme="'primary'"
        icon="plus"
        @click="addSystemApiUser"
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
            {{ row[column.prop] || '--' }}
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
            >
              {{ $t('修改权限') }}
            </bk-button>
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
      v-model="addDialogConfig.visible"
      header-position="left"
      theme="primary"
      :width="480"
      :mask-close="false"
      :title="$t('添加系统 API 用户')"
    >
      <bk-form
        :label-width="200"
        form-type="vertical"
        :model="addDialogConfig.formData"
        ref="validateForm1"
      >
        <bk-form-item
          :label="$t('应用 ID')"
          :required="true"
        >
          <bk-input v-model="addDialogConfig.formData.users"></bk-input>
        </bk-form-item>
        <bk-form-item
          :label="$t('权限')"
          :required="true"
        >
          <bk-input v-model="addDialogConfig.formData.users"></bk-input>
        </bk-form-item>
      </bk-form>
    </bk-dialog>

    <!-- 删除 -->
    <bk-dialog
      v-model="deleteDialogConfig.visible"
      header-position="left"
      theme="primary"
      :width="480"
      :mask-close="false"
      :title="$t('确认删除系统 API 用户')"
      ext-cls="custom-dialog-cls"
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
      <bk-input v-model="deleteDialogConfig.user"></bk-input>
      <template slot="footer">
        <bk-button
          theme="primary"
          :disabled="!isDeleteDisable"
          :loading="deleteDialogConfig.isLoading"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          class="ml10"
          theme="default"
          @click="deleteDialogConfig.visible = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </template>
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
      // api用户列表
      systemApiUserList: [],
      isTableLoading: false,
      addDialogConfig: {
        visible: false,
        formData: {
          // tenant/any
          method: 'tenant',
          users: '',
        },
      },
      deleteDialogConfig: {
        visible: false,
        isLoading: false,
        user: '',
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
    };
  },
  computed: {
    isDeleteDisable() {
      return this.deleteDialogConfig.rowUser === this.deleteDialogConfig.user;
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
    // 添加系统API用户
    addSystemApiUser() {
      this.addDialogConfig.visible = true;
    },
    handleDelete(row) {
      console.log('row', row);
      this.deleteDialogConfig.visible = true;
      this.deleteDialogConfig.rowUser = row.user;
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
