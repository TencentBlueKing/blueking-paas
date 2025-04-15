<template>
  <div class="platform-admin">
    <div class="top-box flex-row justify-content-between">
      <bk-button
        :theme="'primary'"
        icon="plus"
        @click="addFeature"
      >
        {{ $t('添加用户特性') }}
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
            <bk-user-display-name
              v-if="column.prop === 'user' && platformFeature.MULTI_TENANT_MODE"
              :user-id="row[column.prop]"
            ></bk-user-display-name>
            <bk-switcher
              v-else-if="column.prop === 'is_effect'"
              v-model="row[column.prop]"
              theme="primary"
              :disabled="true"
            ></bk-switcher>
            <span v-else-if="column.prop === 'default_feature_flag'">
              {{ row[column.prop] ? $t('开启') : $t('关闭') }}
            </span>
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
      v-model="addDialogConfig.visible"
      header-position="left"
      theme="primary"
      :width="480"
      :mask-close="false"
      :title="$t('添加用户特性')"
    >
      <bk-form
        :label-width="200"
        form-type="vertical"
        :model="addDialogConfig.formData"
        ref="validateForm1"
      >
        <bk-form-item
          :label="$t('用户ID')"
          :required="true"
        >
          <bk-input v-model="addDialogConfig.formData.users"></bk-input>
        </bk-form-item>
      </bk-form>
    </bk-dialog>
  </div>
</template>

<script>
import paginationMixin from '../pagination-mixin.js';
import { mapState } from 'vuex';
export default {
  name: 'UserFeature',
  // 分页逻辑使用mixins导入
  mixins: [paginationMixin],
  data() {
    return {
      isTableLoading: false,
      addDialogConfig: {
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
          label: this.$t('特性名称'),
          prop: 'feature',
        },
        {
          label: this.$t('默认值'),
          prop: 'default_feature_flag',
        },
        {
          label: this.$t('状态'),
          prop: 'is_effect',
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
        const res = await this.$store.dispatch('tenant/getAccountFeatureFlags');
        // mixin-初始化分页数据
        this.pgInitPaginationData(res);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isTableLoading = false;
      }
    },
    // 添加管理员
    addFeature() {
      this.addDialogConfig.visible = true;
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
