<template lang="html">
  <paas-loading :loading="isFirstLoading">
    <div slot="loadingContent">
      <div class="operate-wrapper">
        <bk-button
          theme="primary"
          :disabled="!selectOrderIds.length"
          @click="batchAudit('pass')"
        >
          {{ $t('批量通过') }}
        </bk-button>
        <bk-button
          :disabled="!selectOrderIds.length"
          style="margin-left: 6px;"
          @click="batchAudit('reject')"
        >
          {{ $t('批量驳回') }}
        </bk-button>
      </div>
      <div class="content-wrapper">
        <bk-table
          ref="processTableRef"
          v-bkloading="{ isLoading: tableLoading, opacity: 1 }"
          :data="orderList"
          size="small"
          :class="{ 'set-border': tableLoading }"
          :ext-cls="'ps-permission-table'"
          :pagination="pagination"
          @page-change="pageChange"
          @page-limit-change="limitChange"
          @select="itemHandlerChange"
          @select-all="allHandlerChange"
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
            type="selection"
            width="60"
          />
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
          <bk-table-column
            :label="$t('操作')"
            width="150"
          >
            <template slot-scope="props">
              <div class="table-operate-wrapper">
                <bk-button
                  theme="primary"
                  text
                  @click.stop="showAuditModal(props.row, 'pass')"
                >
                  {{ $t('通过') }}
                </bk-button>
                <bk-button
                  theme="primary"
                  text
                  style="margin-left: 6px;"
                  @click.stop="showAuditModal(props.row, 'reject')"
                >
                  {{ $t('驳回') }}
                </bk-button>
              </div>
            </template>
          </bk-table-column>
        </bk-table>
      </div>

      <bk-dialog
        v-model="approveDialog.visiable"
        :title="approveDialog.title"
        header-position="left"
        :width="approveDialog.width"
        @after-leave="dialogAfterClose"
      >
        <bk-input
          v-model="auditParams.remark"
          :placeholder="$t('请填写原因')"
          :type="'textarea'"
          :rows="5"
          style="margin-bottom: 15px;"
        />
        <p class="ps-tip">
          {{ $t('共') }}{{ auditParams.type === 'pass' ? $t('通过') : $t('驳回') }}
          <span class="span-tip">{{ auditParams.ids.length }}</span> {{ $t('条记录') }}
        </p>
        <div slot="footer">
          <bk-button
            theme="primary"
            :disabled="auditParams.remark === ''"
            :loading="buttonLoading"
            @click="saveAudit"
          >
            {{ $t('确定') }}
          </bk-button>
          <bk-button
            style="margin-left: 6px;"
            @click="cancelAudit"
          >
            {{ $t('取消') }}
          </bk-button>
        </div>
      </bk-dialog>
    </div>
  </paas-loading>
</template>

<script>
    import appBaseInfoMixin from '@/mixins/app-base-mixin';
    import { bus } from '@/common/bus';
    export default {
        mixins: [appBaseInfoMixin],
        data () {
            return {
                isFirstLoading: true,
                orderList: [],
                auditParams: {
                    type: 'pass',
                    ids: [],
                    remark: ''
                },

                pagination: {
                    current: 1,
                    count: 0,
                    limit: 10
                },

                approveDialog: {
                    visiable: false,
                    title: '',
                    width: 480
                },

                selectOrderIds: [],

                tableLoading: false,

                is_up: true,

                buttonLoading: false,

                currentBackup: 1
            };
        },
        watch: {
            '$route' () {
                this.init();
            },
            'pagination.current' (value) {
                this.currentBackup = value;
            }
        },
        mounted () {
            this.init();
        },
        methods: {
            renderHeader (h, { column }) {
                return h(
                    'div',
                    {
                        on: {
                            click: this.sortTab
                        },
                        style: {
                            cursor: this.pagination.count ? 'pointer' : 'not-allowed'
                        }
                    },
                    [
                        h('span', {
                            domProps: {
                                innerHTML: this.$t('申请时间')
                            }
                        }),
                        h('img', {
                            style: {
                                position: 'relative',
                                top: '1px',
                                left: '1px',
                                transform: this.is_up ? 'rotate(0)' : 'rotate(180deg)'
                            },
                            attrs: {
                                src: '/static/images/sort-icon.png'
                            }
                        })
                    ]
                );
            },

            rowClick (row, event, column) {
                row.expanded = !row.expanded;
                this.$refs.processTableRef.toggleRowExpansion(row, row.expanded);
            },

            sortTab () {
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
            getFormatExpiresDisplay (payload) {
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
                        expiresStr = `${curExpires}${this.$t('天')}`;
                }

                return expiresStr;
            },

            /**
             * 分页页码 chang 回调
             *
             * @param {Number} page 页码
             */
            pageChange (page) {
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
            limitChange (currentLimit, prevLimit) {
                this.pagination.limit = currentLimit;
                this.pagination.current = 1;
                this.fetchOrderList(true);
            },

            /**
             * 表格行 chang
             *
             * @param {Array} selection 选中值列表
             * @param {Array} currentRow 当前选中值
             */
            itemHandlerChange (selection, currentRow) {
                this.selectOrderIds.splice(0, this.selectOrderIds.length, ...selection.map(item => item.id));
            },
            /**
             * 表格全选 chang
             *
             * @param {Array} selection 选中值列表
             */
            allHandlerChange (selection) {
                this.selectOrderIds.splice(0, this.selectOrderIds.length, ...selection.map(item => item.id));
            },

            dialogAfterClose () {
                this.auditParams.type = 'pass';
                this.auditParams.remark = '';
                this.auditParams.ids.splice(0, this.auditParams.ids.length, ...[]);
            },

            cancelAudit () {
                this.approveDialog.visiable = false;
            },

            batchAudit (type) {
                this.auditParams.type = type;
                this.auditParams.remark = type === 'pass' ? this.$t('同意') : '';
                this.approveDialog.title = type === 'pass' ? this.$t('通过申请') : this.$t('驳回申请');
                this.auditParams.ids.splice(0, this.auditParams.ids.length, ...this.selectOrderIds);
                this.approveDialog.visiable = true;
            },

            showAuditModal (order, type) {
                this.auditParams.type = type;
                this.auditParams.remark = type === 'pass' ? this.$t('同意') : '';

                this.auditParams.ids.splice(0, this.auditParams.ids.length, ...[order.id]);

                this.approveDialog.title = type === 'pass' ? this.$t('通过申请') : this.$t('驳回申请');
                this.approveDialog.visiable = true;
            },

            async saveAudit () {
                const params = {
                    appCode: this.appCode,
                    type: this.auditParams.type,
                    record_ids: this.auditParams.ids.join(','),
                    remark: this.auditParams.remark
                };
                this.buttonLoading = true;
                try {
                    await this.$store.dispatch('order/operateOrder', params);
                    this.cancelAudit();
                    this.$paasMessage({
                        limit: 1,
                        theme: 'success',
                        message: this.$t('审批成功！')
                    });
                    this.fetchOrderList(true);
                    bus.$emit('update-done-order');
                } catch (e) {
                    this.$paasMessage({
                        limit: 1,
                        theme: 'error',
                        message: `${this.$t('审批失败：')} ${e.detail}`
                    });
                } finally {
                    this.buttonLoading = false;
                }
            },

            async fetchOrderList (isTableLoading = false) {
                this.tableLoading = isTableLoading;
                try {
                    const params = {
                        filterType: 'processing',
                        appCode: this.appCode,
                        limit: this.pagination.limit,
                        offset: (this.pagination.current - 1) * this.pagination.limit,
                        order_by: this.is_up ? '-created' : 'created'
                    };

                    const res = await this.$store.dispatch('order/getOrderList', params);
                    this.pagination.count = res.count
                    ;(res.results || []).forEach(item => {
                        item.isSelected = false;
                        item.expanded = false;
                        item.expires = this.getFormatExpiresDisplay(item.expires);
                        this.$set(item, 'children', [
                            {
                                ip: item.ip || '--',
                                business_interface_user: item.business_interface_user || '--',
                                reason: item.reason || '--',
                                expires: item.expires || '--'
                            }
                        ]);
                    });

                    this.orderList.splice(0, this.orderList.length, ...(res.results || []));
                } catch (res) {
                    this.$paasMessage({
                        limit: 1,
                        theme: 'error',
                        message: this.$t('获取未审批单据失败')
                    });
                } finally {
                    if (isTableLoading) {
                        this.tableLoading = false;
                    }
                }
            },

            init () {
                this.isFirstLoading = true;
                this.fetchOrderList();
                setTimeout(() => {
                    this.isFirstLoading = false;
                    this.$emit('data-ready', 'processing-order');
                }, 1500);
            }
        }
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
        max-width: 200px;
        white-space: nowrap;
        word-wrap: break-word;
        word-break: break-all;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .ps-tip {
        .span-tip {
            padding-right: 4px;
            color: #3a84ff;
            font-weight: bold;
        }
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
