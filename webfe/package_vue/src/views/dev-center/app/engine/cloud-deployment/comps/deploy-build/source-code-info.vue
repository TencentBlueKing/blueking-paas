<template>
  <div class="source-code-info">
    <section>
      <div class="title mb15">{{ $t('源码信息') }}</div>
      <div class="info-wrapper">
        <bk-alert
          type="info"
          :title="$t('该模块部署版本包由“蓝鲸运维开发平台”提供')"
        />
        <a
          v-if="lessCodeFlag && curAppModule.source_origin === GLOBAL.APP_TYPES.LESSCODE_APP"
          :href="lessCodeData.address_in_lesscode || 'javascript:;'"
          :target="lessCodeData.address_in_lesscode ? '_blank' : ''"
          class="link"
          @click="handleLessCode"
        >
          {{ $t('点击前往') }}
          <i class="paasng-icon paasng-jump-link" />
        </a>
      </div>
      <bk-table
        v-bkloading="{ isLoading: isDataLoading }"
        class="mt15"
        :data="packageList"
        :size="'small'"
        :pagination="pagination"
        :outer-border="false"
        @page-change="handlePageChange"
        @page-limit-change="handlePageLimitChange"
        @sort-change="sortChange"
      >
        <div slot="empty">
          <table-empty empty />
        </div>
        <bk-table-column
          :label="$t('版本')"
          :show-overflow-tooltip="true"
        >
          <template slot-scope="props">
            <span>{{ props.row.version || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('文件名')"
          :show-overflow-tooltip="true"
          :render-header="$renderHeader"
        >
          <template slot-scope="props">
            <span>{{ props.row.package_name || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('文件大小')"
          sortable="custom"
          prop="package_size"
          :render-header="$renderHeader"
        >
          <template slot-scope="props">
            <span>{{ props.row.size || '--' }} MB</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('摘要')"
          :show-overflow-tooltip="false"
          :render-header="$renderHeader"
        >
          <template slot-scope="props">
            <span v-bk-tooltips="props.row.sha256_signature || '--'">
              {{ props.row.sha256_signature ? props.row.sha256_signature.substring(0, 8) : '--' }}
            </span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('上传人')"
          :render-header="$renderHeader"
        >
          <template slot-scope="props">
            <span>{{ props.row.operator || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('上传时间')"
          sortable="custom"
          prop="updated"
          :render-header="$renderHeader"
        >
          <template slot-scope="props">
            <span>{{ props.row.updated || '--' }}</span>
          </template>
        </bk-table-column>
      </bk-table>
    </section>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';

export default {
  name: 'SourceCodeInfo',
  mixins: [appBaseMixin],
  data() {
    return {
      isDataLoading: true,
      lessCodeFlag: true,
      packageList: [],
      lessCodeData: {},
      pagination: {
        current: 1,
        count: 0,
        limit: 5,
        limitList: [5, 10, 15, 20],
        order_by: '',
      },
    };
  },
  created() {
    this.getPackageList();
    this.getLessCode();
  },
  methods: {
    // 获取包版本管理数据
    async getPackageList(page) {
      this.isDataLoading = true;
      try {
        const curPage = page || this.pagination.current;
        const params = {
          limit: this.pagination.limit,
          offset: this.pagination.limit * (curPage - 1),
        };

        if (this.pagination.order_by) {
          params.order_by = this.pagination.order_by;
        }

        const res = await this.$store.dispatch('packages/getAppPackageList', {
          isLesscodeApp: this.isLesscodeApp,
          appCode: this.appCode,
          moduleId: this.curModuleId,
          params,
        });

        res.results.forEach((item) => {
          item.size = (item.package_size / 1024 / 1024).toFixed(2);
        });

        this.packageList = res.results;
        this.pagination.count = res.count;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isDataLoading = false;
      }
    },
    async getLessCode() {
      try {
        const resp = await this.$store.dispatch('baseInfo/gitLessCodeAddress', {
          appCode: this.appCode,
          moduleName: this.curModuleId,
        });
        if (resp.address_in_lesscode === '' && resp.tips === '') {
          this.lessCodeFlag = false;
        }
        this.lessCodeData = resp;
      } catch (errRes) {
        this.lessCodeFlag = false;
        console.error(errRes);
      }
    },
    sortChange(params) {
      if (params.order === 'descending') {
        this.pagination.order_by = `-${params.prop}`;
      } else if (params.order === 'ascending') {
        this.pagination.order_by = `${params.prop}`;
      } else {
        this.pagination.order_by = '';
      }
      this.getPackageList();
    },
    handlePageLimitChange(limit) {
      this.pagination.limit = limit;
      this.pagination.current = 1;
      this.getPackageList();
    },
    handlePageChange(newPage) {
      this.pagination.current = newPage;
      this.getPackageList(newPage);
    },
    // 点击前往
    handleLessCode() {
      if (this.lessCodeData.address_in_lesscode) {
        return;
      }
      this.$bkMessage({ theme: 'warning', message: this.$t(this.lessCodeData.tips), delay: 2000, dismissable: false });
    },
  },
};
</script>

<style lang="scss" scoped>
.source-code-info {
  padding-bottom: 24px;
  border-bottom: 1px solid #eaebf0;
  margin-bottom: 24px;
  .title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
  }
  .info-wrapper {
    position: relative;
    .link {
      position: absolute;
      font-size: 12px;
      right: 10px;
      top: 8px;
    }
  }
}
</style>
