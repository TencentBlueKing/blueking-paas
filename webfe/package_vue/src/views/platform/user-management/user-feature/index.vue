<template>
  <div class="platform-admin">
    <div class="top-box flex-row justify-content-between">
      <bk-button
        :theme="'primary'"
        icon="plus"
        @click="showAddDialog"
      >
        {{ $t('添加用户特性') }}
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
        @filter-change="handleFilterChange"
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
            <span v-else-if="column.prop === 'feature'">
              {{ featureMap[row[column.prop]] }}
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
      :auto-close="false"
      :title="$t('添加用户特性')"
      :loading="addDialogConfig.loading"
      @value-change="handleValueChange"
      @confirm="handleConfirm"
    >
      <bk-form
        :label-width="200"
        form-type="vertical"
        :model="addDialogConfig.formData"
        ref="dialogForm"
      >
        <bk-form-item
          :label="`${$t('用户')} ID`"
          :required="true"
          :property="'user'"
          :rules="requiredRule"
          :error-display-type="'normal'"
        >
          <bk-input v-model="addDialogConfig.formData.user"></bk-input>
        </bk-form-item>
        <bk-form-item
          :label="$t('特性名称')"
          :required="true"
          :property="'feature'"
          :rules="requiredRule"
          :error-display-type="'normal'"
        >
          <bk-select v-model="addDialogConfig.formData.feature">
            <bk-option
              v-for="option in featureList"
              :key="option.value"
              :id="option.value"
              :name="option.label"
            ></bk-option>
          </bk-select>
        </bk-form-item>
        <bk-form-item
          :label="$t('状态')"
          :required="true"
          :error-display-type="'normal'"
        >
          <bk-switcher
            v-model="addDialogConfig.formData.is_effect"
            theme="primary"
          ></bk-switcher>
        </bk-form-item>
      </bk-form>
    </bk-dialog>

    <!-- 删除 -->
    <bk-dialog
      v-model="delDialogConfig.visible"
      :width="480"
      theme="primary"
      :mask-close="false"
      header-position="left"
      :title="$t('删除用户特性')"
      ext-cls="delete-dialog-cls"
      @confirm="deleteAccountFeatureFlags"
    >
      <div class="del-txt">
        {{
          $t('确认删除用户（{u}）的特性（{f}）？', {
            u: delDialogConfig.row.user,
            f: featureMap[delDialogConfig.row.feature],
          })
        }}
      </div>
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
        loading: false,
        formData: {
          user: '',
          feature: '',
          is_effect: true,
        },
      },
      delDialogConfig: {
        visible: false,
        row: {},
      },
      featureList: [],
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
    featureMap() {
      return this.featureList.reduce((acc, item) => {
        acc[item.value] = item.label;
        return acc;
      }, {});
    },
    columns() {
      return [
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
          columnKey: 'feature',
          filters: this.featureList,
          filterMultiple: false,
        },
        {
          label: this.$t('默认值'),
          prop: 'default_feature_flag',
        },
        {
          label: this.$t('状态'),
          prop: 'is_effect',
        },
      ];
    },
  },
  created() {
    Promise.all([this.getAccountFeatureFlags(), this.getAccountFeatures()]);
  },
  methods: {
    // 自定义的过滤函数，提供给mixins中使用
    pgFilterFn(item, keyword) {
      return item.user.toLowerCase().includes(keyword);
    },
    // 表格筛选
    handleFilterChange(filds) {
      if (filds.feature) {
        this.pgFieldFilter.filterField = 'feature';
        this.pgFieldFilter.filterValue = filds.feature.length ? filds.feature[0] : null;
      }
      this.pgHandleCombinedSearch();
    },
    // 获取特性列表
    async getAccountFeatures() {
      try {
        const res = await this.$store.dispatch('tenant/getAccountFeatures');
        this.featureList = res.map((v) => {
          return {
            text: v.label,
            ...v,
          };
        });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取平台管理员
    async getAccountFeatureFlags() {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('tenant/getAccountFeatureFlags');
        const srotList = res.sort((a, b) => {
          // 将 is_effect 为 false 的对象排序到后面
          return a.is_effect === b.is_effect ? 0 : a.is_effect ? -1 : 1;
        });
        // mixin-初始化分页数据
        this.pgInitPaginationData(srotList);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        setTimeout(() => {
          this.isTableLoading = false;
        }, 20);
      }
    },
    // 添加管理员
    showAddDialog() {
      this.addDialogConfig.formData = {
        user: '',
        feature: '',
        is_effect: true,
      };
      this.addDialogConfig.visible = true;
    },
    // 添加用户特性
    async addAccountFeatureFlags(data) {
      this.addDialogConfig.loading = true;
      try {
        await this.$store.dispatch('tenant/addAccountFeatureFlags', {
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('添加成功'),
        });
        this.addDialogConfig.visible = false;
        this.getAccountFeatureFlags();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.addDialogConfig.loading = false;
      }
    },
    handleConfirm() {
      this.$refs.dialogForm.validate().then(
        () => {
          this.addAccountFeatureFlags(this.addDialogConfig.formData);
        },
        (validator) => {
          console.error(validator);
        }
      );
    },
    // 删除用户特性
    async deleteAccountFeatureFlags() {
      try {
        await this.$store.dispatch('tenant/deleteAccountFeatureFlags', {
          id: this.delDialogConfig.row?.id,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除成功'),
        });
        this.delDialogConfig.visible = false;
        this.getAccountFeatureFlags();
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    handleDelete(row) {
      this.delDialogConfig.visible = true;
      this.delDialogConfig.row = row;
    },
    handleValueChange(flag) {
      if (!flag) {
        this.$refs?.dialogForm?.clearError();
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
::v-deep .delete-dialog-cls {
  .del-txt {
    color: #4d4f56;
    word-break: break-all;
  }
}
</style>
