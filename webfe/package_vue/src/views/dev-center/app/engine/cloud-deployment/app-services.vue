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
          :data="tableList"
          size="small"
          :pagination="pagination"
          @page-change="pageChange"
          @page-limit-change="limitChange"
          @row-mouse-enter="handleRowMouseEnter"
          @row-mouse-leave="handleRowMouseLeave"
        >
          <div slot="empty">
            <table-empty empty />
          </div>
          <bk-table-column :label="$t('服务名称')">
            <template slot-scope="{row, $index}">
              <div class="flex-row align-items-center">
                <img class="row-img mr10" :src="row.logo" alt="">
                <bk-button text>{{ row.name || '--' }}</bk-button>
                <router-link
                  v-if="$index === rowIndex"
                  target="_blank"
                  :to="{ name: 'serviceInnerPage',
                         params: { category_id: row.category ? row.category.id : '', name: row.name },
                         query: { name: row.display_name } }">
                  <i
                    class="row-icon paasng-icon paasng-page-fill pl5 mt5"
                    v-bk-tooltips="{content: '使用指南'}" />
                </router-link>
              </div>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('预发布环境')">
            <template slot-scope="{row}">
              <span v-if="row.type === 'bound' && row.provision_infos && row.provision_infos.stag">
                <i
                  class="paasng-icon paasng-correct success-icon"
                />
              </span>
              <span v-else>--</span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('生产环境')">
            <template slot-scope="{row}">
              <span v-if="row.type === 'bound' && row.provision_infos && row.provision_infos.prod">
                <i
                  class="paasng-icon paasng-correct success-icon"
                />
              </span>
              <span v-else>--</span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('配置信息')">
            <template slot-scope="{row}">
              <span v-if="row.specifications && row.specifications.length">
                <bk-tag v-for="(item) in row.specifications" :key="item.recommended_value">
                  {{ $t(item.display_name) }} {{ $t(item.recommended_value) }}
                </bk-tag>
              </span>
              <span v-else>--</span>
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
            <template>
              <bk-switcher
                v-model="isShowDate"
                class="bk-small-switcher"
              />
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </paas-content-loader>
  </div>
</template>

<script>import appBaseMixin from '@/mixins/app-base-mixin';

export default {
  components: {
  },
  mixins: [appBaseMixin],
  data() {
    return {
      tableList: [],
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      tableLoading: false,
      isLoading: false,
      rowIndex: '',
      isShowDate: false,
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
      this.gettableList();
      this.isLoading = true;
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.gettableList();
    },

    // 获取表格列表
    async gettableList() {
      this.tableLoading = true;
      try {
        const { appCode } = this;
        const res = await this.$store.dispatch('service/getServicesList', { appCode, moduleId: this.curModuleId });
        // 改造bound数据
        res.bound = (res.bound || []).reduce((p, v) => {
          p.push({ ...v, ...v.service, type: 'bound' });
          return p;
        }, []);
        // 改造shared数据
        res.shared = (res.shared || []).map((e) => {
          e.type = 'shared';
          return e;
        });

        // 改造shared数据
        res.unbound = (res.unbound || []).map((e) => {
          e.type = 'unbound';
          return e;
        });
        this.tableList = [...res.bound, ...res.shared, ...res.unbound];
        console.log('this.tableList', this.tableList);
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

    // 表格鼠标移入
    handleRowMouseEnter(index) {
      this.rowIndex = index;
    },

    // 表格鼠标移出
    handleRowMouseLeave() {
      this.rowIndex = '';
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
    .row-img{
      width: 22px;
      height: 22px;
      border-radius: 50%;
    }
    .row-icon{
      cursor: pointer;
    }

    .success-icon{
      font-size: 24px;
      color: #2DCB56;
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
