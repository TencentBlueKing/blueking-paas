<template lang="html">
  <paas-loading :loading="isFirstLoading">
    <div slot="loadingContent">
      <bk-form form-type="inline">
        <bk-form-item :label="$t('结果')">
          <bk-select
            v-model="filterType"
            style="width: 150px;"
            :placeholder="$t('请选择')"
            :clearable="false"
            @selected="typeSelected"
          >
            <bk-option
              v-for="(option, optionIndex) in list"
              :id="option.id"
              :key="optionIndex"
              :name="option.text"
            />
          </bk-select>
        </bk-form-item>
      </bk-form>
      <div class="content-wrapper">
        <bk-table
          :key="tableKey"
          ref="doneTableRef"
          v-bkloading="{ isLoading: tableLoading, opacity: 1 }"
          :data="orderList"
          size="small"
          :class="{ 'set-border': tableLoading }"
          :pagination="pagination"
          @page-change="pageChange"
          @page-limit-change="limitChange"
          @row-click="rowClick"
        >
          <div slot="empty">
            <table-empty empty />
          </div>
          <bk-table-column
            type="expand"
            width="40"
            align="right"
          >
            <template slot-scope="props">
              <ul
                v-for="(subProps, subPropsIndex) of props.row.children"
                :key="subPropsIndex"
                class="detail-box"
              >
                <li>
                  <span class="key"> {{ $t('申请人IP：') }} </span>
                  <pre class="value">{{ subProps.ip || '--' }}</pre>
                </li>
                <li>
                  <span class="key"> {{ $t('审批人：') }} </span>
                  <pre class="value">{{ subProps.auditor.username || '--' }}</pre>
                </li>
                <li>
                  <span class="key"> {{ $t('业务接口人：') }} </span>
                  <pre class="value">{{ subProps.business_interface_user || '--' }}</pre>
                </li>
                <li>
                  <span class="key"> {{ $t('添加原因：') }} </span>
                  <pre class="value">{{ subProps.reason || '--' }}</pre>
                </li>
                <li>
                  <span class="key"> {{ $t('有效时间：') }} </span>
                  <pre class="value">{{ subProps.expires || '--' }}</pre>
                </li>
              </ul>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('申请人')"
            :render-header="$renderHeader"
          >
            <template slot-scope="props">
              <span>{{ props.row.applicant || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('公司')">
            <template slot-scope="props">
              <span>{{ props.row.company || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('业务')">
            <template slot-scope="props">
              <span>{{ props.row.business || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('申请时间')"
            :render-header="renderHeader"
          >
            <template slot-scope="props">
              <span>{{ props.row.created || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('有效时间')"
            :render-header="$renderHeader"
          >
            <template slot-scope="props">
              <span>{{ props.row.expires || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('结果')">
            <template slot-scope="props">
              <p>
                <span
                  v-if="props.row.status === 'pass'"
                  class="ps-text-primary"
                > {{ $t('已通过') }} </span>
                <span
                  v-else
                  class="ps-text-danger"
                > {{ $t('被驳回') }} </span>
              </p>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </div>
  </paas-loading>
</template>

<script>
import appBaseInfoMixin from '@/mixins/app-base-mixin';
import { bus } from '@/common/bus';
export default {
  mixins: [appBaseInfoMixin],
  data() {
    return {
      isFirstLoading: true,
      orderList: [],
      filterType: 'done_all',
      list: [
        {
          id: 'done_all',
          text: this.$t('全部'),
        },
        {
          id: 'pass',
          text: this.$t('通过'),
        },
        {
          id: 'reject',
          text: this.$t('驳回'),
        },
      ],

      tableLoading: false,
      is_up: true,
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      currentBackup: 1,
      tableKey: 0,
    };
  },
  watch: {
    '$route'() {
      this.init();
    },
    'pagination.current'(value) {
      this.currentBackup = value;
    },
  },
  mounted() {
    this.init();
    bus.$on('update-done-order', () => {
      this.tableKey = new Date().getTime();
      this.fetchOrderList();
    });
  },
  methods: {
    renderHeader(h, { column }) {
      return h(
        'div',
        {
          on: {
            click: this.sortTab,
          },
          style: {
            cursor: this.pagination.count ? 'pointer' : 'not-allowed',
          },
        },
        [
          h('span', {
            domProps: {
              innerHTML: this.$t('申请时间'),
            },
          }),
          h('img', {
            style: {
              position: 'relative',
              top: '1px',
              left: '1px',
              transform: this.is_up ? 'rotate(0)' : 'rotate(180deg)',
            },
            attrs: {
              src: '/static/images/sort-icon.png',
            },
          }),
        ],
      );
    },

    rowClick(row, event, column) {
      row.expanded = !row.expanded;
      this.$refs.doneTableRef.toggleRowExpansion(row, row.expanded);
    },

    sortTab() {
      if (!this.pagination.count) {
        return;
      }
      this.is_up = !this.is_up;
      this.pagination.limit = 10;
      this.pagination.current = 1;
      this.fetchOrderList(true);
    },

    /**
               * 有效期时间显示格式化
               *
               * @param {String} payload 有效期时间字符
               *
               * @return {String} expiresStr 格式化后的有效期时间显示
               */
    getFormatExpiresDisplay(payload) {
      if (!payload) {
        return this.$t('永久');
      }
      const curExpires = Number(payload.split(' ')[0]);
      const MONTH_DAY = 30;
      let expiresStr = '';
      const months = Math.floor(curExpires / MONTH_DAY);
      switch (months) {
        case 3:
          expiresStr = this.$t('3个月');
          break;
        case 6:
          expiresStr = this.$t('6个月');
          break;
        case 12:
          expiresStr = this.$t('1年');
          break;
        default:
          expiresStr = `${curExpires}天`;
      }

      return expiresStr;
    },

    /**
               * 分页页码 chang 回调
               *
               * @param {Number} page 页码
               */
    pageChange(page) {
      if (this.currentBackup === page) {
        return;
      }
      this.pagination.current = page;
      this.fetchOrderList(true);
    },

    /**
               * 分页limit chang 回调
               *
               * @param {Number} currentLimit 新limit
               * @param {Number} prevLimit 旧limit
               */
    limitChange(currentLimit, prevLimit) {
      this.pagination.limit = currentLimit;
      this.pagination.current = 1;
      this.fetchOrderList(true);
    },

    typeSelected(value, options) {
      this.filterType = value;
      this.fetchOrderList(true);
    },

    async fetchOrderList(isTableLoading = false) {
      this.tableLoading = isTableLoading;
      try {
        const params = {
          filterType: this.filterType,
          appCode: this.appCode,
          limit: this.pagination.limit,
          offset: (this.pagination.current - 1) * this.pagination.limit,
          order_by: this.is_up ? '-created' : 'created',
        };

        const res = await this.$store.dispatch('order/getOrderList', params);
        this.pagination.count = res.count
        ;(res.results || []).forEach((item) => {
          item.expanded = false;
          item.expires = this.getFormatExpiresDisplay(item.expires);
          this.$set(item, 'children', [
            {
              ip: item.ip || '--',
              business_interface_user: item.business_interface_user || '--',
              reason: item.reason || '--',
              auditor: item.auditor || '--',
              expires: item.expires || '--',
            },
          ]);
        });
        this.orderList.splice(0, this.orderList.length, ...(res.results || []));
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: this.$t('获取已审批单据失败'),
        });
      } finally {
        if (isTableLoading) {
          this.tableLoading = false;
        }
      }
    },
    init() {
      this.isFirstLoading = true;
      this.fetchOrderList();
      setTimeout(() => {
        this.isFirstLoading = false;
        this.$emit('data-ready', 'done-order');
      }, 1500);
    },
  },
};
</script>

  <style lang="scss" scoped>
      .content-wrapper {
          margin-top: 16px;
          .bk-table {
              &.set-border {
                  border-right: 1px solid #dfe0e5;
                  border-bottom: 1px solid #dfe0e5;
              }
          }
      }

      .reason {
          max-width: 180px;
          white-space: nowrap;
          word-wrap: break-word;
          word-break: break-all;
          overflow: hidden;
          text-overflow: ellipsis;
      }

      .detail-box {
          padding: 5px 20px 5px 0;
          margin: 0 -30px;
          background-color: #fafbfd;

          li {
              display: flex;
              padding: 0 10px;
              font-size: 13px;
              margin: 3px 0;
          }

          .key {
              display: block;
              min-width: 100px;
              line-height: 30px;
              font-weight: bold;
              text-align: right;
          }

          .value {
              line-height: 26px;
              display: block;
              padding-top: 4px;
              max-width: 700px;
          }
      }
  </style>

