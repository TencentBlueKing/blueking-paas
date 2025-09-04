<template>
  <div class="platform-admin">
    <bk-alert
      type="info"
      :title="
        $t('平台通过用户特性功能，将部分功能以灰度方式开放给用户。添加用户特性后，用户可以在产品页面上访问相关功能。')
      "
    ></bk-alert>
    <div class="top-box flex-row justify-content-between">
      <bk-button
        :theme="'primary'"
        icon="plus"
        @click="showAddDialog"
      >
        {{ $t('添加用户特性') }}
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
              v-if="column.prop === 'user' && isMultiTenantDisplayMode"
              :user-id="row[column.prop]"
            ></bk-user-display-name>
            <bk-switcher
              v-else-if="column.prop === 'is_effect'"
              v-model="row[column.prop]"
              theme="primary"
              @change="switcherChange(row, $event)"
            ></bk-switcher>
            <span v-else-if="column.prop === 'default_feature_flag'">
              {{ row[column.prop] ? $t('开启') : $t('关闭') }}
            </span>
            <span v-else-if="column.prop === 'feature'">
              {{ featureMap[row[column.prop]] || '--' }}
            </span>
            <span v-else>{{ column.prop === 'userId' ? row['user'] : row[column.prop] || '--' }}</span>
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
          :label="$t('用户')"
          :required="true"
          :property="'users'"
          :rules="requiredRule"
          :error-display-type="'normal'"
        >
          <user
            v-model="addDialogConfig.formData.users"
            :placeholder="$t('请输入用户')"
            :multiple="false"
            :empty-text="$t('无匹配人员')"
          />
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
          <p
            v-if="addDialogConfig.formData.feature"
            slot="tip"
            class="f12"
            style="color: #979ba5"
          >
            {{ $t('特性的默认状态为：{f}', { f: curFeatureSelected.default_flag ? $t('开启') : $t('关闭') }) }}
          </p>
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
      <bk-alert
        v-if="curFeatureSelected.default_flag === addDialogConfig.formData.is_effect"
        class="mt10"
        type="warning"
        :title="$t('状态和特性默认值一致，添加后将不会产生任何效果。')"
      ></bk-alert>
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
        <p>
          <span>{{ $t('确认删除用户') }}</span>
          &nbsp;
          <bk-user-display-name
            v-if="isMultiTenantDisplayMode"
            :user-id="delDialogConfig.row.user"
          ></bk-user-display-name>
          <span v-else>{{ delDialogConfig.row.user }}</span>
          &nbsp;
          <span>{{ `${$t('的特性')}？` }}</span>
        </p>
        <p class="mt8">
          {{ $t('删除用户的特性') }}（{{ featureMap[delDialogConfig.row.feature] }}）{{ $t('将恢复默认值') }}：
          <span>{{ delDialogConfig.row.default_feature_flag ? $t('开启') : $t('关闭') }}</span>
          <span>{{ localLanguage === 'en' ? '.' : '。' }}</span>
        </p>
      </div>
    </bk-dialog>
  </div>
</template>

<script>
import paginationMixin from '../pagination-mixin.js';
import User from '@/components/user';
import { mapState, mapGetters } from 'vuex';
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
      addDialogConfig: {
        visible: false,
        loading: false,
        formData: {
          users: [],
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
      userSearchValues: [],
    };
  },
  computed: {
    ...mapState({
      localLanguage: (state) => state.localLanguage,
    }),
    ...mapGetters(['isMultiTenantDisplayMode']),
    featureMap() {
      return this.featureList.reduce((acc, item) => {
        acc[item.value] = item.label;
        return acc;
      }, {});
    },
    curFeatureSelected() {
      return this.featureList.find((v) => v.value === this.addDialogConfig.formData.feature) || {};
    },
    columns() {
      const baseColumns = [
        {
          label: `${this.$t('用户')} ID`,
          prop: 'userId',
        },
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

      // 如果 isMultiTenantDisplayMode 为 false，过滤掉 'user' 列
      if (!this.isMultiTenantDisplayMode) {
        return baseColumns.filter((column) => column.label !== this.$t('用户'));
      }
      return baseColumns;
    },
  },
  watch: {
    userSearchValues(newVal) {
      this.pgSearchValue = newVal.join();
      // 分页搜索
      this.pgHandleCombinedSearch();
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
        users: [],
        feature: '',
        is_effect: true,
      };
      this.addDialogConfig.visible = true;
    },
    // 添加用户特性
    async eidtiAddAccountFeatureFlags(data, type = 'add') {
      this.addDialogConfig.loading = true;
      const messageTxt = data.is_effect ? this.$t('特性已开启') : this.$t('特性已关闭');
      try {
        await this.$store.dispatch('tenant/addAccountFeatureFlags', {
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: type === 'add' ? this.$t('添加成功') : messageTxt,
        });
        this.addDialogConfig.visible = false;
        this.getAccountFeatureFlags();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.addDialogConfig.loading = false;
      }
    },
    async handleConfirm() {
      try {
        await this.$refs.dialogForm.validate();
        const { users, feature, is_effect } = this.addDialogConfig.formData;
        const params = {
          user: users?.join(),
          feature,
          is_effect,
        };
        this.eidtiAddAccountFeatureFlags(params);
      } catch (error) {
        console.error('Form validation failed:', error);
      }
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
    // 切换状态
    switcherChange(row, val) {
      const { user, feature } = row;
      const params = {
        user,
        feature,
        is_effect: val,
      };
      this.eidtiAddAccountFeatureFlags(params, 'feature');
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
::v-deep .delete-dialog-cls {
  .del-txt {
    margin-top: 8px;
    font-size: 12px;
    color: #63656e;
    line-height: 22px;
    word-break: break-all;
    .mt8 {
      margin-top: 8px;
    }
  }
}
</style>
