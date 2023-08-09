<template>
  <div class="services-container">
    <paas-content-loader
      class="app-container image-content"
      :is-loading="isLoading"
      placeholder="roles-loading"
    >
      <div class="middle ps-main">
        <bk-table
          v-bkloading="{ isLoading: tableLoading, opacity: 1 }"
          :data="tablelList"
          size="small"
          :pagination="pagination"
          @page-change="pageChange"
          @page-limit-change="limitChange"
        >
          <div slot="empty">
            <table-empty empty />
          </div>
          <bk-table-column :label="$t('服务名称')">
            <template slot-scope="props">
              {{ props.row.name || '--' }}
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('预发布环境')">
            <template slot-scope="props">
              {{ props.row.username || '--' }}
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('生产环境')">
            <span>******</span>
          </bk-table-column>
          <bk-table-column :label="$t('配置信息')">
            <template slot-scope="props">
              {{ props.row.description || '--' }}
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('共享信息')">
            <template slot-scope="props">
              {{ props.row.description || '--' }}
            </template>
          </bk-table-column>
          <bk-table-column
            width="120"
            :label="$t('启/停')"
          >
            <template slot-scope="props">
              <bk-button
                class="mr10"
                text
                theme="primary"
                @click="handleEdit(props.row)"
              >
                {{ $t('编辑') }}
              </bk-button>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </paas-content-loader>
  </div>
</template>

<script>
export default {
  components: {
  },
  data() {
    return {
      tablelList: [],
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      tableLoading: false,
    };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
    curAppCode() {
      return this.$store.state.curAppCode;
    },
  },
  watch: {
    curAppCode() {
      this.getTablelList();
      this.isLoading = true;
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.getTablelList();
    },

    // 获取表格列表
    async getTablelList() {
      this.tableLoading = true;
      try {
        const { appCode } = this;
        const res = await this.$store.dispatch('credential/getImageCredentialList', { appCode });
        this.tablelList = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      } finally {
        this.tableLoading = false;
        setTimeout(() => {
          this.isLoading = false;
        }, 500);
      }
    },
    pageChange(page) {
      if (this.currentBackup === page) {
        return;
      }
      this.pagination.current = page;
    },

    limitChange(currentLimit) {
      this.pagination.limit = currentLimit;
      this.pagination.current = 1;
    },

  },
};
</script>

<style lang="scss" scoped>
  .services-container{
    .ps-top-bar{
      padding: 0 20px;
    }
    .image-content{
      background: #fff;
      padding-top: 0;
    }
  }
    .header-title {
        display: flex;
        align-items: center;
        .app-code {
            color: #979BA5;
        }
        .arrows {
            margin: 0 9px;
            transform: rotate(-90deg);
            font-size: 12px;
            font-weight: 600;
            color: #979ba5;
        }
    }
</style>
