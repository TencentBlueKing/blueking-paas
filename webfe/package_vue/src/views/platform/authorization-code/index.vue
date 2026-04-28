<template>
  <div class="right-main authorization-code p-24">
    <bk-alert
      class="mb-16"
      type="info"
      :title="$t('为了规范应用 ID 命名，特定前缀（如 bk-）仅分配给官方应用，需经平台管理员审核发放授权码。')"
    ></bk-alert>

    <div class="card-style p-24 mb-16">
      <div class="card-title">{{ $t('生成授权码') }}</div>
      <bk-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="mt-16"
        form-type="vertical"
      >
        <bk-form-item
          property="appCode"
          :required="true"
          :label="$t('应用 ID')"
          :error-display-type="'normal'"
        >
          <bk-input
            v-model="form.appCode"
            :placeholder="$t('请输入用户申请的应用 ID，如 bk-monitor')"
          />
        </bk-form-item>
        <bk-button
          class="mt-16"
          theme="primary"
          @click="generateCode"
        >
          {{ $t('生成授权码') }}
        </bk-button>
        <!-- 授权码生成结果 -->
        <div
          v-if="generatedCode"
          class="code-result mt-16"
        >
          <span class="code-label">{{ $t('授权码') }}：</span>
          <span class="code-value">{{ generatedCode }}</span>
          <div class="code-actions">
            <bk-button
              theme="default"
              v-copy="generatedCode"
            >
              <i class="bk-icon icon-copy"></i>
              {{ $t('复制') }}
            </bk-button>
            <bk-button
              class="ml-12"
              theme="default"
              @click="continueGenerate"
            >
              <i class="bk-icon icon-plus"></i>
              {{ $t('继续生成') }}
            </bk-button>
          </div>
        </div>
      </bk-form>
    </div>

    <!-- 已生成授权码 -->
    <div class="card-style p-24">
      <div class="card-title mb-16">{{ $t('已生成授权码') }}</div>
      <bk-input
        v-model="searchValue"
        :placeholder="$t('搜索应用 ID 或授权码')"
        :right-icon="'bk-icon icon-search'"
        clearable
      />
      <bk-table
        class="mt-16"
        :data="filterTableData"
      >
        <div slot="empty">
          <table-empty
            :keyword="searchValue"
            @clear-filter="searchValue = ''"
          />
        </div>
        <bk-table-column
          :label="$t('授权码')"
          prop="code"
          min-width="180"
        >
          <template #default="{ row }">
            <span>{{ row.code }}</span>
            <i
              class="copy-icon bk-icon icon-copy ml-10"
              v-copy="row.code"
            ></i>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('应用 ID')"
          prop="appCode"
          min-width="140"
        ></bk-table-column>
        <bk-table-column
          :label="$t('生成时间')"
          prop="createTime"
          min-width="160"
        ></bk-table-column>
        <bk-table-column
          :label="$t('状态')"
          prop="isUsed"
          min-width="100"
        >
          <template #default="{ row }">
            <bk-tag
              style="margin-left: 0"
              :theme="row.isUsed ? 'success' : 'default'"
            >
              {{ row.isUsed ? $t('已使用') : $t('未使用') }}
            </bk-tag>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('操作')"
          width="100"
        >
          <template #default="{ row }">
            <bk-button
              text
              :disabled="row.isUsed"
              @click="deleteCode(row)"
            >
              {{ $t('删除') }}
            </bk-button>
          </template>
        </bk-table-column>
      </bk-table>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      form: { appCode: '' },
      rules: {
        appCode: [
          {
            required: true,
            message: this.$t('请输入应用 ID'),
            trigger: 'blur',
          },
        ],
      },
      generatedCode: '',
      searchValue: '',
      tableData: [],
    };
  },
  computed: {
    filterTableData() {
      const keyword = this.searchValue.trim().toLowerCase();
      if (!keyword) return this.tableData;
      return this.tableData.filter(
        (item) => item.code.toLowerCase().includes(keyword) || item.appCode.toLowerCase().includes(keyword)
      );
    },
  },
  created() {
    this.fetchCodeList();
  },
  methods: {
    // 获取授权码列表
    async fetchCodeList() {
      try {
        const res = await this.$store.dispatch('tenantConfig/getAuthorizationCodeList');
        this.tableData = (res || []).map((item) => ({
          id: item.id,
          code: item.auth_code,
          appCode: item.app_code,
          isUsed: item.is_used,
          createTime: item.created,
        }));
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 生成授权码
    async generateCode() {
      await this.$refs.formRef.validate().then(
        async () => {
          try {
            const res = await this.$store.dispatch('tenantConfig/generateAuthorizationCode', {
              data: { app_code: this.form.appCode.trim() },
            });
            this.generatedCode = res.auth_code || '';
            this.fetchCodeList();
          } catch (e) {
            this.catchErrorHandler(e);
          }
        },
        (validator) => {
          console.log(validator);
        }
      );
    },
    continueGenerate() {
      this.generatedCode = '';
      this.form.appCode = '';
    },
    // 删除授权码
    async deleteCode(row) {
      const h = this.$createElement;
      this.$bkInfo({
        title: this.$t('是否删除该授权码？'),
        extCls: 'paas-custom-del-info-cls',
        theme: 'danger',
        width: 400,
        okText: this.$t('删除'),
        subHeader: h('div', { style: { textAlign: 'center' } }, [
          h('p', [h('span', { class: ['label'] }, `${this.$t('授权码')}：`), h('span', row.code)]),
        ]),
        confirmFn: async () => {
          try {
            await this.$store.dispatch('tenantConfig/deleteAuthorizationCode', {
              id: row.id,
            });
            this.$bkMessage({ theme: 'success', message: this.$t('删除成功') });
            this.fetchCodeList();
          } catch (e) {
            this.catchErrorHandler(e);
          }
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.authorization-code {
  .card-title {
    font-size: 14px;
    font-weight: 600;
    color: #313238;
  }

  .code-result {
    height: 56px;
    display: flex;
    align-items: center;
    padding: 0 16px;
    border: 1px solid #3a84ff;
    border-radius: 2px;
    background-color: #f0f5ff;

    .code-label {
      font-size: 14px;
      color: #000;
      line-height: 20px;
    }

    .code-value {
      font-size: 14px;
      color: #1768ef;
      font-weight: 500;
      line-height: 20px;
    }

    .code-actions {
      margin-left: auto;
      i.icon-copy {
        font-size: 14px;
        transform: translateY(-2px);
      }
    }
  }

  .copy-icon {
    cursor: pointer;
    color: #4d4f56;

    &:hover {
      color: #3a84ff;
    }
  }
}
</style>
