<template>
  <div class="paasng-api-panel">
    <div class="search-wrapper">
      <bk-button
        theme="primary"
        :disabled="isApplyDisabled"
        @click="handleBatchApply"
      >
        {{ $t('批量申请') }}
      </bk-button>
      <bk-button
        style="margin-left: 6px;"
        theme="primary"
        :disabled="isRenewalDisabled"
        @click="handleBatchRenewal"
      >
        {{ $t('批量续期') }}
      </bk-button>
      <section class="fr">
        <div class="label mr15">
          {{ $t('类型') }}
        </div>
        <div class="select-wrapper">
          <bk-select
            v-model="typeValue"
            searchable
            :clearable="false"
            @selected="handleSelect"
          >
            <bk-option
              v-for="option in typeList"
              :id="option.id"
              :key="option.id"
              :name="option.name"
            />
          </bk-select>
        </div>
        <div class="checkbox-wrapper">
          <bk-checkbox
            v-model="isRenewalPerm"
            :true-value="true"
            :false-value="false"
            @change="handleChange"
          >
            {{ $t('可续期权限') }}
          </bk-checkbox>
        </div>
        <div class="input-wrapper">
          <bk-input
            v-model="searchValue"
            :placeholder="$t('输入API名称或描述，按Enter搜索')"
            clearable
            right-icon="paasng-icon paasng-search"
            @input="handleSearch"
          />
        </div>
        <div class="search-button">
          <bk-button
            theme="primary"
            @click="handlePageSearch"
          >
            {{ $t('查询') }}
          </bk-button>
        </div>
      </section>
    </div>
    <paas-content-loader
      :is-loading="loading"
      :offset-top="0"
      placeholder="cloud-api-inner-loading"
      :height="300"
    >
      <div>
        <paasng-alert
          :title="$t('若有效期限不足180天，但应用仍在访问 API，有效期限将自动延长至 180 天（不限次数）。')"
          style="margin-bottom: 16px;width: 100%"
        />
        <bk-table
          ref="permRef"
          :key="tableKey"
          :data="tableList"
          :size="'small'"
          :empty-text="$t('暂无数据')"
          :pagination="pagination"
          :show-pagination-info="true"
          :header-border="false"
          @filter-change="filterChange"
          @page-change="pageChange"
          @page-limit-change="limitChange"
          @selection-change="handleSelectionChange"
        >
          <div slot="empty">
            <table-empty
              :keyword="tableEmptyConf.keyword"
              :abnormal="tableEmptyConf.isAbnormal"
              @reacquire="fetchList"
              @clear-filter="clearFilterKey"
            />
          </div>
          <bk-table-column
            label="id"
            type="selection"
            :selectable="selectable"
            width="60"
          >
          </bk-table-column>
          <bk-table-column
            :label="$t('API类型')"
            :render-header="$renderHeader"
          >
            <template slot-scope="props">
              {{ typeMap[props.row.type] }}
            </template>
          </bk-table-column>
          <template v-if="tableList.length > 0">
            <bk-table-column
              :label="isComponentApi ? $t('系统') : $t('网关')"
              min-width="100"
              :prop="isComponentApi ? 'system_name' : 'api_name'"
              :column-key="isComponentApi ? 'system_name' : 'api_name'"
              :filters="nameFilters"
              :filter-method="nameFilterMethod"
              :filter-multiple="true"
            >
              <template slot-scope="props">
                <template v-if="isComponentApi">
                  {{ props.row.system_name }}
                </template>
                <template v-else>
                  {{ props.row.api_name }}
                </template>
              </template>
            </bk-table-column>
          </template>
          <template v-else>
            <bk-table-column
              :label="isComponentApi ? $t('系统') : $t('网关')"
              min-width="100"
            >
              <template slot-scope="props">
                <template v-if="isComponentApi">
                  {{ props.row.system_name }}
                  <template v-if="!!props.row.tag">
                    <span :class="[{ inner: [$t('内部版'), $t('互娱外部版')].includes(props.row.tag) }, { clound: [$t('上云版'), $t('互娱外部上云版')].includes(props.row.tag) }]">
                      {{ props.row.tag }}
                    </span>
                  </template>
                </template>
                <template v-else>
                  {{ props.row.api_name }}
                </template>
              </template>
            </bk-table-column>
          </template>
          <bk-table-column
            label="API"
            min-width="120"
          >
            <template slot-scope="props">
              <template v-if="props.row.doc_link">
                <a
                  target="_blank"
                  :href="props.row.doc_link"
                >
                  <span v-html="highlight(props.row)" />
                  <i
                    class="fa fa-book"
                    aria-hidden="true"
                  />
                </a>
              </template>
              <template v-else>
                <span v-html="highlight(props.row)" />
              </template>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('描述')"
            min-width="120"
          >
            <template slot-scope="props">
              <span
                v-bk-tooltips="{ content: props.row.description, disabled: props.row.description === '' }"
                v-html="highlightDesc(props.row)"
              />
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('权限等级')"
            :render-header="$renderHeader"
          >
            <template slot-scope="props">
              <span :class="['special', 'sensitive'].includes(props.row.permission_level)">{{ levelMap[props.row.permission_level] }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('权限期限')"
            :render-header="$renderHeader"
          >
            <template slot-scope="props">
              {{ getComputedExpires(props.row) }}
            </template>
          </bk-table-column>
          <template v-if="tableList.length > 0">
            <bk-table-column
              :label="$t('状态')"
              prop="permission_status"
              column-key="status"
              :filters="statusFilters"
              :filter-method="statusFilterMethod"
              :filter-multiple="true"
              :render-header="$renderHeader"
            >
              <template slot-scope="props">
                <template v-if="props.row.permission_status === 'owned'">
                  <span class="paasng-icon paasng-pass" /> {{ $t('已拥有') }}
                </template>
                <template v-else-if="props.row.permission_status === 'unlimited'">
                  <span class="paasng-icon paasng-pass" /> {{ $t('无限制') }}
                </template>
                <template v-else-if="props.row.permission_status === 'need_apply'">
                  <span class="paasng-icon paasng-reject" /> {{ $t('未申请') }}
                </template>
                <template v-else-if="props.row.permission_status === 'expired'">
                  <span class="paasng-icon paasng-reject" /> {{ $t('已过期') }}
                </template>
                <template v-else-if="props.row.permission_status === 'rejected'">
                  <span class="paasng-icon paasng-reject" /> {{ $t('已拒绝') }}
                </template>
                <template v-else>
                  <round-loading ext-cls="applying" /> {{ $t('申请中') }}
                </template>
              </template>
            </bk-table-column>
          </template>
          <template v-else>
            <bk-table-column
              :label="$t('状态')"
              :render-header="$renderHeader"
            >
              <template slot-scope="props">
                <template v-if="props.row.permission_status === 'owned'">
                  <span class="paasng-icon paasng-pass" /> {{ $t('已拥有') }}
                </template>
                <template v-else-if="props.row.permission_status === 'unlimited'">
                  <span class="paasng-icon paasng-pass" /> {{ $t('无限制') }}
                </template>
                <template v-else-if="props.row.permission_status === 'need_apply'">
                  <span class="paasng-icon paasng-reject" /> {{ $t('未申请') }}
                </template>
                <template v-else-if="props.row.permission_status === 'expired'">
                  <span class="paasng-icon paasng-reject" /> {{ $t('已过期') }}
                </template>
                <template v-else-if="props.row.permission_status === 'rejected'">
                  <span class="paasng-icon paasng-reject" /> {{ $t('已拒绝') }}
                </template>
                <template v-else>
                  <round-loading ext-cls="applying" /> {{ $t('申请中') }}
                </template>
              </template>
            </bk-table-column>
          </template>
          <bk-table-column
            :label="$t('操作')"
            :width="localLanguage === 'en' ? 130 : 110"
          >
            <template slot-scope="{ row }">
              <div class="table-operate-buttons">
                <bk-button
                  style="padding: 0 0 0 10px;"
                  theme="primary"
                  :disabled="row.applyDisabled"
                  size="small"
                  text
                  @click="handleApply(row)"
                >
                  <span
                    v-bk-tooltips="{
                      content: $t(row.applyTips),
                      disabled: !row.applyDisabled
                    }"> {{ $t('申请') }} </span>
                </bk-button>
                <bk-button
                  style="padding: 0 0 0 10px;"
                  theme="primary"
                  :disabled="row.renewDisabled"
                  size="small"
                  text
                  @click="handleRenewal(row)"
                >
                  <span
                    v-bk-tooltips="{
                      content: $t(row.renewTips),
                      disabled: !row.renewDisabled
                    }"> {{ $t('续期') }} </span>
                </bk-button>
              </div>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </paas-content-loader>

    <!-- 申请权限 -->
    <batch-dialog
      :show.sync="applyDialog.visiable"
      :title="applyDialog.title"
      :rows="applyDialog.rows"
      :api-id="applyDialog.superiorId"
      :api-name="applyDialog.superiorName"
      :app-code="appCode"
      :is-component="isComponentApi"
      @on-apply="handleSuccessApply"
      @after-leave="handleAfterLeave"
    />

    <renewal-dialog
      :show.sync="renewalDialog.visiable"
      :title="renewalDialog.title"
      :rows="renewalDialog.rows"
      :api-name="renewalDialog.name"
      :app-code="appCode"
      :is-component="isComponentApi"
      @on-renewal="handleSuccessRenewal"
      @after-leave="handleRenewalAfterLeave"
    />
  </div>
</template>

<script>import RenewalDialog from './batch-renewal-dialog';
import BatchDialog from './batch-apply-dialog';
import PaasngAlert from './paasng-alert';
import { clearFilter } from '@/common/utils';
import { formatRenewFun, formatApplyFun } from '@/common/cloud-api';

export default {
  name: '',
  components: {
    RenewalDialog,
    PaasngAlert,
    BatchDialog,
  },
  data() {
    return {
      loading: false,
      apiList: [],
      allData: [],
      tableList: [],
      searchValue: '',
      isFilter: false,
      pagination: {
        current: 1,
        limit: 10,
        count: 0,
      },
      allChecked: false,
      indeterminate: false,
      renewalDialog: {
        visiable: false,
        title: '',
        rows: [],
        name: '',
      },
      typeList: [
        {
          id: 'gateway',
          name: this.$t('网关API'),
        },
        {
          id: 'component',
          name: this.$t('组件API'),
        },
      ],
      typeMap: {
        component: this.$t('组件API'),
        gateway: this.$t('网关API'),
      },
      typeValue: 'gateway',
      isRenewalPerm: false,
      levelMap: {
        normal: this.$t('普通'),
        special: this.$t('特殊'),
        sensitive: this.$t('敏感'),
        unlimited: this.$t('无限制'),
      },
      statusFilters: [
        { text: this.$t('已拥有'), value: 'owned' },
        { text: this.$t('无限制'), value: 'unlimited' },
        { text: this.$t('未申请'), value: 'need_apply' },
        { text: this.$t('已过期'), value: 'expired' },
        { text: this.$t('已拒绝'), value: 'rejected' },
        { text: this.$t('申请中'), value: 'pending' },
      ],
      is_up: true,
      nameFilters: [],
      tableKey: -1,
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
      allFilterData: {},
      selectedList: [],
      // 申请权限弹窗数据
      applyDialog: {
        visiable: false,
        title: '',
        rows: [],
        superiorId: '',
        superiorName: '',
      },
    };
  },
  computed: {
    isComponentApi() {
      return this.typeValue === 'component';
    },
    appCode() {
      return this.$route.params.id;
    },
    isPageDisabled() {
      return this.tableList.every(item => !item.permission_action) || !this.tableList.length;
    },
    curDispatchMethod() {
      return this.typeValue === 'component' ? 'getSysAppPermissions' : 'getAppPermissions';
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    // 是否允许批量申请
    isApplyDisabled() {
      return !this.selectedList.some(item => item.applyDisabled === false);
    },
    // 是否允许批量续期
    isRenewalDisabled() {
      return !this.selectedList.some(item => item.renewDisabled === false);
    },
  },
  watch: {
    '$route'() {
      this.init();
    },
    searchValue(newVal, oldVal) {
      if (newVal === '' && oldVal !== '' && this.isFilter) {
        this.allData = this.apiList;
        this.pagination.count = this.apiList.length;
        this.pagination.current = 1;
        const start = this.pagination.limit * (this.pagination.current - 1);
        const end = start + this.pagination.limit;
        this.tableList.splice(0, this.tableList.length, ...this.allData.slice(start, end));
        this.isFilter = false;
      }
      if (newVal === '') {
        this.updateTableEmptyConfig();
      }
    },
    allData(value) {
      this.tableKey = +new Date();
    },
  },
  created() {
    this.init();
    this.compare = p => (m, n) => {
      const a = m[p] ? m[p] : 0;
      const b = n[p] ? n[p] : 0;
      return this.is_up ? a - b : b - a;
    };
    this.compareName = p => (m, n) => {
      const a = m[p].slice(0, 1).charCodeAt();
      const b = n[p].slice(0, 1).charCodeAt();
      return a - b;
    };
  },
  methods: {
    handleBatchRenewal() {
      if (!this.selectedList.length) {
        return;
      }
      this.renewalDialog.visiable = true;
      this.renewalDialog.title = this.$t('批量续期权限');
      this.renewalDialog.rows = [...this.selectedList];
    },

    // 批量申请权限
    handleBatchApply() {
      if (!this.selectedList.length) {
        return;
      }
      this.applyDialog.visiable = true;
      this.applyDialog.title = this.$t('批量申请权限');
      this.applyDialog.rows = [...this.selectedList];
    },

    nameFilterMethod(value, row, column) {
      const { property } = column;
      return row[property] === value;
    },

    statusFilterMethod(value, row, column) {
      const { property } = column;
      return row[property] === value;
    },

    filterChange(filters) {
      Object.entries(filters).forEach((item) => {
        const [name, value] = item;
        this.allFilterData[name] = value;
      });
      this.updateTableEmptyConfig();
    },

    handleSelect(value, option) {
      this.pagination = Object.assign({}, {
        current: 1,
        limit: 10,
        count: 0,
      });
      this.nameFilters = [];
      this.selectedList = [];
      this.fetchList();
      this.fetchFilterList();
    },

    sortTable() {
      if (!this.pagination.count) {
        return;
      }
      this.is_up = !this.is_up;
    },

    renderExpireHeader(h, { column }) {
      return h(
        'div',
        {
          on: {
            click: this.sortTable,
          },
          style: {
            cursor: this.pagination.count ? 'pointer' : 'not-allowed',
          },
        },
        [
          h('span', {
            domProps: {
              innerHTML: this.$t('权限期限'),
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

    handleSuccessRenewal() {
      this.renewalDialog.visiable = false;
      this.allChecked = false;
      this.indeterminate = false;
      this.fetchList(this.id);
    },

    handleRenewalAfterLeave() {
      this.renewalDialog = Object.assign({}, {
        visiable: false,
        title: '',
        rows: [],
        name: '',
      });
    },

    handleChange(newVal, oldVal, val) {
      if (newVal) {
        this.allData = this.apiList.filter(item => item.permission_action === 'renew');
      } else {
        this.allData = this.apiList;
      }
      this.initPageConf();
      this.tableList = this.getDataByPage();
      this.updateTableEmptyConfig();
    },

    /**
             * 初始化弹层翻页条
             */
    initPageConf() {
      this.pagination.current = 1;
      const total = this.allData.length;
      this.pagination.count = total;
    },

    /**
             * 翻页回调
             *
             * @param {number} page 当前页
             */
    pageChange(page = 1) {
      this.allChecked = false;
      this.indeterminate = false;
      this.tableList.forEach((api) => {
        if (api.hasOwnProperty('checked')) {
          api.checked = false;
        }
      });
      this.pagination.current = page;
      const data = this.getDataByPage(page);
      this.tableList.splice(0, this.tableList.length, ...data);
    },

    /**
             * 获取当前这一页的数据
             *
             * @param {number} page 当前页
             *
             * @return {Array} 当前页数据
             */
    getDataByPage(page) {
      if (!page) {
        this.pagination.current = page = 1;
      }
      let startIndex = (page - 1) * this.pagination.limit;
      let endIndex = page * this.pagination.limit;
      if (startIndex < 0) {
        startIndex = 0;
      }
      if (endIndex > this.allData.length) {
        endIndex = this.allData.length;
      }
      return this.allData.slice(startIndex, endIndex);
    },

    limitChange(currentLimit, prevLimit) {
      this.allChecked = false;
      this.indeterminate = false;
      this.tableList.forEach((api) => {
        if (api.hasOwnProperty('checked')) {
          api.checked = false;
        }
      });
      this.pagination.limit = currentLimit;
      this.pagination.current = 1;
      this.pageChange(this.pagination.current);
    },

    getComputedExpires(payload) {
      if (!payload.expires_in) {
        if (payload.permission_status === 'owned') {
          return this.$t('永久');
        }
        return '--';
      }
      return `${Math.ceil(payload.expires_in / (24 * 3600))}${this.$t('天')}`;
    },

    async handlePageSearch() {
      this.selectedList = [];
      try {
        await this.fetchList();
        this.handleSearch();
        if (this.isRenewalPerm) {
          this.allData = this.apiList.filter(item => item.permission_action === 'renew');
        } else {
          this.allData = this.apiList;
        }
        this.initPageConf();
        this.tableList = this.getDataByPage();
        this.handleSearch();
      } catch (e) {
        console.error(e);
      }
    },

    handleSearch() {
      if (this.searchValue === '') {
        return;
      }
      this.isFilter = true;
      this.allData = [...this.apiList.filter(api => api.name.indexOf(this.searchValue) !== -1 || api.description.indexOf(this.searchValue) !== -1)];
      this.pagination.count = this.allData.length;

      this.pagination.current = 1;

      const start = this.pagination.limit * (this.pagination.current - 1);
      const end = start + this.pagination.limit;
      this.tableList.splice(0, this.tableList.length, ...this.allData.slice(start, end));
      this.updateTableEmptyConfig();
    },

    init() {
      this.fetchList();
    },

    async fetchList() {
      this.loading = true;
      try {
        const res = await this.$store.dispatch(`cloudApi/${this.curDispatchMethod}`, { appCode: this.appCode })
                    ;(res.data || []).forEach((item) => {
          item.type = this.typeValue;
        });
        // 权限续期处理
        if (res.data.length) {
          res.data = res.data.map((v) => {
            // 申请
            const apply = formatApplyFun(v.permission_status);
            // 续期
            const renew = formatRenewFun(v.permission_status);
            return {
              ...v,
              applyDisabled: apply.disabled,
              applyTips: apply.tips,
              renewDisabled: renew.disabled,
              renewTips: renew.tips,
            };
          });
        }
        // this.apiList = Object.freeze(res.data.sort(this.compareName('name')))
        this.apiList = Object.freeze(res.data);
        this.apiList.forEach((item) => {
          if (this.isComponentApi) {
            if (!this.nameFilters.map(_ => _.value).includes(item.system_name)) {
              this.nameFilters.push({
                text: item.system_name,
                value: item.system_name,
              });
            }
          } else {
            if (!this.nameFilters.map(_ => _.value).includes(item.api_name)) {
              this.nameFilters.push({
                text: item.api_name,
                value: item.api_name,
              });
            }
          }
        });
        if (this.isRenewalPerm) {
          this.allData = res.data.filter(item => item.permission_action === 'renew');
        } else {
          this.allData = res.data;
        }
        this.initPageConf();
        this.tableList = this.getDataByPage();
        this.indeterminate = false;
        this.allChecked = false;
        this.tableKey = +new Date();
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.catchErrorHandler(e);
      } finally {
        this.loading = false;
        this.$emit('data-ready');
      }
    },

    handleRenewal(item) {
      this.renewalDialog.visiable = true;
      this.renewalDialog.title = this.$t('权限续期');
      this.renewalDialog.rows = [item];
      this.renewalDialog.name = this.isComponentApi ? item.system_name : item.api_name;
    },

    resetSelectedAPIList() {
      this.tableList.forEach((item) => {
        this.$set(item, 'checked', false);
      });
      this.allChecked = false;
      this.indeterminate = false;
    },

    highlight({ name }) {
      if (this.isFilter) {
        return name.replace(this.searchValue, `<marked>${this.searchValue}</marked>`);
      }
      return name;
    },

    highlightDesc({ description }) {
      if (this.isFilter) {
        if (description !== '') {
          return description.replace(this.searchValue, `<marked>${this.searchValue}</marked>`);
        }
        return '--';
      }
      return description || '--';
    },
    clearFilterKey() {
      this.searchValue = '';
      this.isRenewalPerm = false;
      this.allFilterData = {};
      this.$refs.permRef.clearFilter();
      if (this.$refs.permRef && this.$refs.permRef.$refs.tableHeader) {
        const { tableHeader } = this.$refs.permRef.$refs;
        clearFilter(tableHeader);
      }
      this.fetchList();
    },

    updateTableEmptyConfig() {
      const isTableFilter = this.isFilterCriteria();

      if (this.searchValue || this.isRenewalPerm || isTableFilter) {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      this.tableEmptyConf.keyword = '$CONSTANT';
    },

    // 表头是否存在筛选条件
    isFilterCriteria() {
      let isFilter = false;
      for (const key in this.allFilterData) {
        if (this.allFilterData[key].length) {
          isFilter = true;
        }
      };
      return isFilter;
    },

    // 勾选是否禁用
    selectable(row) {
      return !row.applyDisabled || !row.renewDisabled;
    },

    // 表格change事件
    handleSelectionChange(selected) {
      this.selectedList = selected;
    },

    // 申请权限弹窗
    handleApply(item) {
      const id = this.isComponentApi ? 'system_id' : 'gateway_id';
      const name = this.isComponentApi ? 'system_name' : 'api_name';
      // 获取对应权限的网关、组件数据
      this.applyDialog.superiorId = item[id];
      this.applyDialog.superiorName = item[name];
      this.applyDialog.visiable = true;
      this.applyDialog.title = this.$t('申请权限');
      this.applyDialog.rows = [item];
    },

    // 申请
    handleSuccessApply() {
      this.applyDialog.visiable = false;
      this.allChecked = false;
      // 获取列表
      this.fetchList(this.id);
    },

    // 取消
    handleAfterLeave() {
      this.applyDialog = Object.assign({}, {
        visiable: false,
        title: '',
        rows: [],
        superiorId: '',
        superiorName: '',
      });
    },
  },
};
</script>

<style lang="scss" scoped>
    .search-wrapper {
        margin-bottom: 16px;
        .label,
        .select-wrapper,
        .checkbox-wrapper,
        .search-button,
        .input-wrapper {
            display: inline-block;
            vertical-align: top;
        }
        .label {
            line-height: 32px;
        }
        .select-wrapper {
            width: 200px;
        }
        .checkbox-wrapper {
            margin: 0 15px;
            line-height: 32px;
        }
        .input-wrapper {
            width: 300px;
        }
        .search-button {
            margin-left: 10px;
        }
    }

    .table-operate-buttons {
        position: relative;
        left: -12px;
    }

    span.sensitive {
        color: #ff0000;
    }

    span.inner {
        color: rgb(58, 171, 255);
        opacity: .7;
    }

    span.clound {
        color: #45e35f;
    }

    span.paasng-pass {
        position: relative;
        top: 1px;
        color: #2dcb56;
        font-size: 14px;
    }

    span.paasng-reject {
        position: relative;
        top: 1px;
        color: #ea3636;
        font-size: 14px;
    }

    .applying {
        position: relative;
        top: -1px;
    }
</style>

<style>
    marked {
        background: yellow;
        color: black;
    }
</style>
