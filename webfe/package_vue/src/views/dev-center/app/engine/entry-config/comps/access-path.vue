<template>
  <div class="right-main">
    <paas-content-loader
      class="app-container middle path-exempt-wrapper"
      :is-loading="isPathExemptLoading"
      placeholder="exempt-loading"
    >
      <section class="path-table">
        <div class="header-info mt10">
          <bk-alert
            type="info"
            :title="$t('路径添加到豁免路径配置中后，访问这些路径时不会再校验用户信息，预发布环境、生产环境同时生效')">
          </bk-alert>
        </div>
        <template v-if="!isPathExemptLoading">
          <div class="ps-table-bar">
            <bk-button
              theme="primary"
              @click="showUserModal"
            >
              <i class="paasng-icon paasng-plus mr5" /> {{ $t('新增路径前缀') }}
            </bk-button>
            <bk-button
              style="margin-left: 6px;"
              :disabled="isBatchDisabled"
              @click="batchDelete"
            >
              {{ $t('批量删除') }}
            </bk-button>
            <bk-input
              v-model="keyword"
              style="width: 240px; float: right;"
              :placeholder="$t('输入关键字，按Enter搜索')"
              :right-icon="'paasng-icon paasng-search'"
              clearable
              @enter="searchUserPermissionList"
            />
          </div>

          <bk-table
            v-bkloading="{ isLoading: tableLoading, opacity: 1 }"
            :data="userPermissionList"
            size="small"
            :class="{ 'set-border': tableLoading }"
            :pagination="pagination"
            @page-change="pageChange"
            @page-limit-change="limitChange"
            @select="handlerChange"
            @select-all="handlerAllChange"
          >
            <div slot="empty">
              <table-empty
                :keyword="tableEmptyConf.keyword"
                :abnormal="tableEmptyConf.isAbnormal"
                @reacquire="fetchPathExemptList(true)"
                @clear-filter="clearFilterKey"
              />
            </div>
            <bk-table-column
              type="selection"
              width="60"
              align="left"
            />
            <bk-table-column
              :label="$t('路径前缀')"
              :render-header="$renderHeader"
            >
              <template slot-scope="{ row }">
                <span>{{ row.path || '--' }}</span>
              </template>
            </bk-table-column>
            <bk-table-column
              :label="$t('添加者')"
              :render-header="$renderHeader"
            >
              <template slot-scope="props">
                <span>{{ props.row.owner.username || '--' }}</span>
              </template>
            </bk-table-column>
            <bk-table-column
              :label="$t('添加时间')"
              :render-header="renderHeader"
            >
              <template slot-scope="{ row }">
                <span v-bk-tooltips="row.created">{{ smartTime(row.created,'fromNow') }}</span>
              </template>
            </bk-table-column>
            <bk-table-column
              :label="$t('添加原因')"
              :render-header="$renderHeader"
            >
              <template slot-scope="props">
                <bk-popover>
                  <div class="reason">
                    {{ props.row.desc ? props.row.desc : '--' }}
                  </div>
                  <div
                    slot="content"
                    style="white-space: normal;"
                  >
                    {{ props.row.desc ? props.row.desc : '--' }}
                  </div>
                </bk-popover>
              </template>
            </bk-table-column>
            <bk-table-column
              :label="$t('操作')"
              width="100"
            >
              <template slot-scope="props">
                <section>
                  <bk-button
                    theme="primary"
                    text
                    @click="handleUpdate(props.row)"
                  >
                    {{ $t('更新') }}
                  </bk-button>
                  <bk-button
                    theme="primary"
                    text
                    style="margin-left: 4px;"
                    @click="showRemoveModal(props.row)"
                  >
                    {{ $t('删除') }}
                  </bk-button>
                </section>
              </template>
            </bk-table-column>
          </bk-table>
        </template>
      </section>
    </paas-content-loader>

    <bk-dialog
      v-model="removeUserDialog.visiable"
      width="500"
      :title="$t('确定删除？')"
      :theme="'primary'"
      :mask-close="false"
      :header-position="'left'"
      :loading="removeUserDialog.isLoading"
      @confirm="removePath"
      @after-leave="afterCloseRemove"
    >
      <div class="tl">
        {{ $t('删除后，访问路径') }}[{{ curPathParams.path || '--' }}]{{ $t('需提供用户登录态并在用户白名单内。') }}
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="batchRemovePathDialog.visiable"
      width="600"
      :title="$t('确定批量删除？')"
      :theme="'primary'"
      :mask-close="false"
      :header-position="'left'"
      :loading="batchRemovePathDialog.isLoading"
      @confirm="batchRemovePath"
    >
      <div class="tl">
        {{ $t('删除后，访问这些路径需提供用户登录态并在用户白名单内。') }}
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="addPathDialog.visiable"
      width="600"
      :title="addPathDialog.title"
      header-position="left"
      :theme="'primary'"
      :mask-close="false"
      :close-icon="!addPathDialog.isLoading"
      :loading="addPathDialog.isLoading"
      @confirm="addPath"
      @cancel="cancelAddPath"
      @after-leave="afterAddClose"
    >
      <template
        v-if="addPathDialog.showForm"
      >
        <section style="min-height: 140px;">
          <bk-form
            ref="addUserForm"
            :label-width="100"
            :model="curPathParams"
            form-type="vertical"
          >
            <bk-form-item
              :label="$t('路径前缀')"
              :rules="pathParamRules.path"
              :required="true"
              :property="'path'"
            >
              <bk-input v-model="curPathParams.path" />
              <p class="ps-tip mt10">
                {{ $t('以反斜杠(/)开始、结束，如：/api/user/ 表示以 /api/user/ 开头的所有路径均被豁免') }}
              </p>
            </bk-form-item>
            <bk-form-item
              :label="$t('添加原因')"
              :rules="pathParamRules.desc"
              :required="true"
              :property="'desc'"
            >
              <bk-input
                v-model="curPathParams.desc"
                type="textarea"
                :placeholder="$t('请输入200个字符以内')"
                :maxlength="200"
              />
            </bk-form-item>
            <p style="margin-top: 10px; font-size: 12px; font-weight: 600;">
              {{ $t('注意：路径被豁免后会完全失去白名单保护，请确保已对其进行额外的安全加固，否则可能引起严重后果。') }}
            </p>
          </bk-form>
        </section>
      </template>
    </bk-dialog>
  </div>
</template>

<script>import appBaseMixin from '@/mixins/app-base-mixin';
export default {
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: false,
      userPermissionList: [],
      isPathExemptLoading: true,
      isAjaxSending: false,
      keyword: '',
      curPathParams: {
        path: '',
        desc: '',
      },
      pathParamRules: {
        path: [
          {
            required: true,
            message: this.$t('请输入'),
            trigger: 'blur',
          },
          {
            // validator: value => /(^\/(.+\/)+)$/.test(value),
            // 避免 ReDOS 风险
            validator: value => value.startsWith('/') && value.endsWith('/') && value.length > 2,
            message: this.$t('路径前缀格式错误，以反斜杠(/)开始、结束，如：/api/user/'),
            trigger: 'blur',
          },
        ],
        desc: [
          {
            required: true,
            message: this.$t('请输入'),
            trigger: 'blur',
          },
        ],
      },
      addPathDialog: {
        visiable: false,
        isLoading: false,
        showForm: false,
        title: this.$t('新增豁免路径前缀'),
        action: 'create',
        id: 0,
      },
      removeUserDialog: {
        visiable: false,
        isLoading: false,
        id: 0,
      },

      tableLoading: false,

      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },

      is_up: true,

      isFilter: false,

      currentBackup: 1,

      currentSelectList: [],

      batchRemovePathDialog: {
        visiable: false,
        isLoading: false,
      },
      isUseUserPermission: true,
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
    };
  },
  computed: {
    isBatchDisabled() {
      return this.currentSelectList.length < 1 || this.userPermissionList.length < 1;
    },
  },
  watch: {
    '$route'() {
      this.init();
    },
    'pagination.current'(value) {
      this.currentBackup = value;
    },
    keyword(newVal, oldVal) {
      if (newVal === '' && oldVal !== '') {
        if (this.isFilter) {
          this.pagination.current = 1;
          this.pagination.limit = 10;
          this.fetchPathExemptList(true);
          this.isFilter = false;
        }
      }
    },
  },
  mounted() {
    this.init();
  },
  methods: {
    sortTab() {
      if (!this.pagination.count) {
        return;
      }
      this.is_up = !this.is_up;
      this.pagination.current = 1;
      this.pagination.limit = 10;
      this.fetchPathExemptList(true);
    },

    renderHeader(h) {
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
              innerHTML: this.$t('添加时间'),
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
      this.fetchPathExemptList(true);
    },

    batchDelete() {
      if (this.currentSelectList.length === 1) {
        const { id, desc, path } = this.currentSelectList[0];
        this.curPathParams = Object.assign({}, { desc, path });
        this.removeUserDialog.visiable = true;
        this.removeUserDialog.id = id;
        return;
      }
      this.batchRemovePathDialog.visiable = true;
    },

    /**
     * 分页limit chang 回调
     *
     * @param {Number} currentLimit 新limit
     * @param {Number} prevLimit 旧limit
     */
    limitChange(currentLimit) {
      this.pagination.limit = currentLimit;
      this.pagination.current = 1;
      this.fetchPathExemptList(true);
    },

    searchUserPermissionList() {
      if (this.keyword === '') {
        return;
      }
      this.isFilter = true;
      this.pagination.limit = 10;
      this.pagination.current = 1;
      this.fetchPathExemptList(true);
    },

    afterAddClose() {
      this.addPathDialog.showForm = false;
      this.addPathDialog.title = this.$t('新增豁免路径前缀');
      this.addPathDialog.action = 'create';
      this.addPathDialog.id = 0;
      this.curPathParams = {
        path: '',
        desc: '',
      };
    },

    clearKeyword() {
      this.keyword = '';
    },

    showUserModal() {
      this.addPathDialog.visiable = true;
      this.addPathDialog.showForm = true;
    },

    handlerAllChange(selection) {
      this.currentSelectList = [...selection];
    },

    handlerChange(selection) {
      this.currentSelectList = [...selection];
    },

    showRemoveModal(user) {
      const { path, desc } = user;
      this.curPathParams = Object.assign({}, { path, desc });
      this.removeUserDialog.visiable = true;
      this.removeUserDialog.id = user.id;
    },

    handleUpdate(payload) {
      const { path, desc, id } = payload;
      this.curPathParams = Object.assign({}, {
        path,
        desc,
      });
      this.addPathDialog.title = this.$t('更新豁免路径前缀');
      this.addPathDialog.action = 'update';
      this.addPathDialog.id = id;
      this.addPathDialog.showForm = true;
      this.addPathDialog.visiable = true;
    },

    closePermission() {
      this.userPermissionDialog.visiable = false;
    },

    async fetchPathExemptList(isTableLoading = false) {
      this.tableLoading = isTableLoading;
      try {
        const params = {
          appCode: this.appCode,
          limit: this.pagination.limit,
          offset: (this.pagination.current - 1) * this.pagination.limit,
          order_by: this.is_up ? '-created' : 'created',
          search_term: this.keyword,
          restriction_type: 'user',
        };

        const res = await this.$store.dispatch('user/getExemptList', params);
        this.pagination.count = res.count;
        this.userPermissionList.splice(0, this.userPermissionList.length, ...(res.results || []));
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('获取豁免路径失败：')} ${e.detail}`,
        });
      } finally {
        this.tableLoading = false;
        this.isPathExemptLoading = false;
      }
    },

    addPath() {
      this.addPathDialog.isLoading = true;
      setTimeout(() => {
        this.$refs.addUserForm.validate().then(
          () => {
            this.submitPathParams();
            this.addPathDialog.isLoading = false;
          },
          () => {
            this.addPathDialog.isLoading = false;
          },
        );
      }, 200);
    },

    async submitPathParams() {
      if (this.addPathDialog.action === 'create') {
        this.addPathDialog.isLoading = true;
        try {
          await this.$store.dispatch('user/createExempt', {
            appCode: this.appCode,
            restriction_type: 'user',
            data: {
              ...this.curPathParams,
            },
          });
          this.pagination.current = 1;
          this.pagination.limit = 10;
          this.fetchPathExemptList(true);
          this.$paasMessage({
            theme: 'success',
            message: this.$t('新增路径前缀成功！'),
          });
        } catch (e) {
          this.$paasMessage({
            limit: 1,
            theme: 'error',
            message: `${this.$t('新增路径前缀失败：')} ${e.detail}`,
          });
        } finally {
          this.addPathDialog.isLoading = false;
          this.cancelAddPath();
        }
      } else {
        this.addPathDialog.isLoading = true;
        try {
          await this.$store.dispatch('user/updateExempt', {
            appCode: this.appCode,
            restriction_type: 'user',
            strategy_id: this.addPathDialog.id,
            data: {
              ...this.curPathParams,
            },
          });
          this.pagination.current = 1;
          this.pagination.limit = 10;
          this.fetchPathExemptList(true);
          this.$paasMessage({
            theme: 'success',
            message: this.$t('更新成功！'),
          });
        } catch (e) {
          this.$paasMessage({
            limit: 1,
            theme: 'error',
            message: `${this.$t('更新失败：')} ${e.detail}`,
          });
        } finally {
          this.addPathDialog.isLoading = false;
          this.cancelAddPath();
        }
      }
    },

    async batchRemovePath() {
      this.batchRemovePathDialog.isLoading = true;
      try {
        await this.$store.dispatch('user/batchDeleteExempt', {
          appCode: this.appCode,
          restriction_type: 'user',
          id: this.currentSelectList.map(item => item.id),
        });
        this.pagination.current = 1;
        this.pagination.limit = 10;
        this.currentSelectList = [];
        this.fetchPathExemptList(true);
        this.$paasMessage({
          theme: 'success',
          message: this.$t('批量删除成功！'),
        });
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('批量删除失败：')} ${e.detail}`,
        });
      } finally {
        this.batchRemovePathDialog.isLoading = false;
        this.batchRemovePathDialog.visiable = false;
      }
    },

    async removePath() {
      this.removeUserDialog.isLoading = true;
      try {
        await this.$store.dispatch('user/deleteExempt', {
          appCode: this.appCode,
          restriction_type: 'user',
          strategy_id: this.removeUserDialog.id,
        });
        this.pagination.current = 1;
        this.pagination.limit = 10;
        this.currentSelectList = [];
        this.fetchPathExemptList(true);
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除成功！'),
        });
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('删除失败：')} ${e.detail}`,
        });
      } finally {
        this.removeUserDialog.isLoading = false;
        this.removeUserDialog.visiable = false;
      }
    },

    afterCloseRemove() {
      this.curPathParams = {
        path: '',
        desc: '',
      };
      this.removeUserDialog.id = 0;
    },

    cancelAddPath() {
      this.addPathDialog.visiable = false;
    },

    async checkUserPermissin() {
      try {
        const res = await this.$store.dispatch('user/checkUserPermissin', {
          appCode: this.appCode,
        });
        this.isUseUserPermission = res.is_enabled;
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.detail,
        });
      }
    },

    async init() {
      if (this.curAppInfo.feature.ACCESS_CONTROL_EXEMPT_MODE) {
        await this.checkUserPermissin();
        if (this.isUseUserPermission) {
          this.fetchPathExemptList();
        }
      }
    },

    clearFilterKey() {
      this.keyword = '';
    },

    updateTableEmptyConfig() {
      this.tableEmptyConf.keyword = this.keyword;
    },
  },
};
</script>

  <style lang="scss" scoped>
      .bk-table {
          &.set-border {
              border-right: 1px solid #dfe0e5;
              border-bottom: 1px solid #dfe0e5;
          }
      }

      .path-exempt-wrapper {
          background: #fff;
          margin: 15px 0px 0px;
          padding: 10px 24px 20px;
          min-height: 300px !important;
          .header-info {
              label {
                  display: block;
                  color: #313238;
                  font-weight: bold;
              }
              p {
                  margin-top: 5px;
                  color: #979ba5;
                  font-size: 12px;
              }
          }
      }

      .container {
          width: 100%;
          padding: 20px 0;
          color: #666;
      }

      .ps-table-bar {
          padding: 16px 30px;
          margin: 0 -30px;

      }

      .middle {
          border-bottom: none;
      }

      .reason {
          max-width: 150px;
          white-space: nowrap;
          word-wrap: break-word;
          word-break: break-all;
          overflow: hidden;
          text-overflow: ellipsis;
      }
  </style>
