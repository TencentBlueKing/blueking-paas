<template>
  <div class="clund-image-list">
    <section class="top-action-bar">
      <div class="left">
        <bk-select
          v-model="moduleName"
          style="width: 150px"
          :clearable="false"
          ext-cls="module-select-custom"
          prefix-icon="paasng-icon paasng-project"
          @selected="handleChangeModule"
        >
          <bk-option
            v-for="option in curAppModuleList"
            :key="option.name"
            :id="option.name"
            :name="option.name"
          ></bk-option>
        </bk-select>
        <bk-input
          class="ml10"
          style="width: 320px"
          v-model="searchValue"
          right-icon="paasng-icon paasng-search"
          @enter="handleSearch"
        ></bk-input>
      </div>
      <div class="right">
        <!-- 构建历史 -->
        <div
          class="deploy-history flex-row align-items-center"
          :class="{ 'disabled': isCustomImage }"
          v-bk-tooltips="{
            content: $t('当前模块直接提供镜像部署，无构建历史'),
            disabled: !isCustomImage,
          }"
          @click="handleDeploymentHistory"
        >
          <i class="paasng-icon paasng-lishijilu"></i>
          <p>{{ $t('构建历史') }}</p>
        </div>
      </div>
    </section>
    <div class="table-wrapper mt15">
      <bk-table
        v-bkloading="{ isLoading: isTableLoading }"
        ext-cls="image-table-cls"
        :data="imageList"
        :outer-border="false"
        :size="'small'"
        :pagination="pagination"
        :height="imageList.length ? '' : '520px'"
        :show-overflow-tooltip="true"
        @page-change="handlePageChange"
        @page-limit-change="handlePageLimitChange"
        @expand-change="handleExpandChange"
      >
        <div slot="empty">
          <table-empty
            v-if="searchValue"
            :keyword="tableEmptyConf.keyword"
            :abnormal="tableEmptyConf.isAbnormal"
            @reacquire="getImageList"
            @clear-filter="handleClearFilter"
          />
          <table-empty
            v-else
            :explanation="$t('目前仅支持基于源码构建的镜像')"
            empty
          />
        </div>
        <bk-table-column
          type="expand"
          width="30"
          class="expand-image"
        >
          <template slot-scope="{ row }">
            <div
              class="image-info"
              v-bkloading="{ isLoading: row.isLoading }"
            >
              <section class="left-info">
                <bk-form :model="row.detail">
                  <bk-form-item :label="`${$t('镜像仓库')}：`">
                    <span class="form-text">{{ row.detail.image_info.repository || '--' }}</span>
                  </bk-form-item>
                  <bk-form-item :label="`${$t('镜像 tag')}：`">
                    <span class="form-text">{{ row.detail.image_info.tag || '--' }}</span>
                  </bk-form-item>
                  <bk-form-item :label="`${$t('大小（B）')}：`">
                    <span class="form-text">{{ row.detail.image_info.size || '--' }}</span>
                  </bk-form-item>
                  <bk-form-item :label="`${$t('更新时间')}：`">
                    <span class="form-text">{{ row.detail.image_info.updated || '--' }}</span>
                  </bk-form-item>
                  <bk-form-item :label="`${$t('摘要')}：`">
                    <span class="form-text">{{ row.detail.image_info.digest || '--' }}</span>
                  </bk-form-item>
                  <bk-form-item :label="`${$t('备注')}：`">
                    <span class="form-text">{{ row.detail.image_info.invoke_message || '--' }}</span>
                  </bk-form-item>
                </bk-form>
              </section>
              <div
                class="fright-middle fright-last"
              >
                <h3> {{ $t('部署记录') }} </h3>
                <ul class="dynamic-list">
                  <template v-if="row.detail.deploy_records?.length">
                    <li
                      v-for="(item, itemIndex) in row.detail.deploy_records"
                      :key="itemIndex"
                    >
                      <p class="dynamic-content">
                        {{ item.operator }} {{ $t('部署到') }}{{item.environment === 'stag' ? $t('预发布环境') : $t('生产环境')}}
                        <span class="dynamic-time">{{ item.at }}</span>
                      </p>
                    </li>
                  </template>
                  <template v-else>
                    <table-empty empty />
                  </template>
                </ul>
              </div>
            </div>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('镜像 tag')"
          prop="tag"
          :show-overflow-tooltip="true"
        />
        <bk-table-column
          width="120"
          :label="$t('大小（B）')"
          prop="size"
          sortable
        />
        <bk-table-column
          width="160"
          :label="$t('更新时间')"
          prop="updated"
          :show-overflow-tooltip="true"
        />
        <bk-table-column
          :label="$t('摘要')"
          prop="digest"
          :show-overflow-tooltip="true"
        />
      </bk-table>
    </div>
  </div>
</template>

<script>import appBaseMixin from '@/mixins/app-base-mixin';
export default {
  name: 'ClundImageList',
  mixins: [appBaseMixin],
  data() {
    return {
      moduleName: '',
      searchValue: '',
      isTableLoading: false,
      imageList: [],
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
    };
  },
  computed: {
    isCustomImage() {
      const curModule = this.curAppModuleList.find(module => module.name === this.moduleName);
      return curModule?.web_config?.runtime_type === 'custom_image';
    },
  },
  watch: {
    searchValue(val) {
      if (!val) {
        this.getImageList();
      }
    },
    $route() {
      this.init();
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.moduleName = this.curModuleId;
      this.getImageList();
    },
    /**
     * 切换模块
     */
    handleChangeModule() {
      this.getImageList();
    },
    /**
     * 获取镜像列表
     */
    async getImageList(page = 1) {
      const curPage = page || this.pagination.current;

      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('imageManage/getImageList', {
          appCode: this.appCode,
          moduleName: this.moduleName,
          pageParams: {
            limit: this.pagination.limit,
            offset: this.pagination.limit * (curPage - 1),
            search_term: this.searchValue,
          },
        });
        this.imageList = res.results.map(image => ({
          isLoading: false,
          detail: {
            build_records: [],
            deploy_records: [],
            image_info: {},
          },
          ...image,
        }));
        this.pagination.count = res.count;
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isTableLoading = false;
        this.$emit('hide-loading');
      }
    },

    /**
     * 获取镜像详情
     */
    async getImageDetail(id) {
      try {
        const res = await this.$store.dispatch('imageManage/getImageDetail', {
          appCode: this.appCode,
          moduleName: this.moduleName,
          buildId: id,
        });
        this.imageList.forEach((image) => {
          if (image.id === id) {
            image.detail = res;
          }
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.imageList.forEach((image) => {
          if (image.id === id) {
            image.isLoading = false;
          }
        });
      }
    },

    /** 搜索 */
    handleSearch() {
      this.getImageList();
    },

    /** 页码改变 */
    handlePageChange(newPage) {
      this.pagination.current = newPage;
      this.getImageList(newPage);
    },

    /** 页容量改变 */
    handlePageLimitChange(limit) {
      this.pagination.limit = limit;
      this.pagination.current = 1;
      this.getImageList(this.pagination.current);
    },

    /** 当前行展开事件 */
    handleExpandChange(row) {
      // 如果存在数据则不请求
      if (Object.keys(row.detail.image_info).length) {
        return;
      }
      row.isLoading = true;
      this.getImageDetail(row.id);
    },

    /** 清空筛选条件 */
    handleClearFilter() {
      this.searchValue = '';
    },

    updateTableEmptyConfig() {
      if (this.searchValue) {
        this.tableEmptyConf.keyword = 'placeholder';
        return;
      }
      this.tableEmptyConf.keyword = '';
    },

    // 部署历史
    handleDeploymentHistory() {
      this.$router.push({
        name: 'cloudAppBuildHistory',
        params: {
          id: this.curAppCode,
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.clund-image-list {
  padding: 24px;

  .top-action-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    .left {
      display: flex;
    }
    .right {
      .deploy-history {
        cursor: pointer;
        font-size: 14px;
        color: #3a84ff;
        i {
          transform: translateY(0);
          margin-left: 12px;
          margin-right: 5px;
        }
        &.disabled {
          color: #dcdee5;
          cursor: not-allowed;
        }
      }
    }
  }

  .image-info {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    padding: 10px 24px;

    .left-info {
      /deep/ .bk-form .bk-label {
        font-size: 12px;
        padding-right: 12px;
        color: #63656e;
      }
      .form-text {
        color: #313238;
      }
      /deep/ .bk-form-item + .bk-form-item {
        margin-top: 0;
      }
    }
  }

  .image-table-cls /deep/ .bk-table-body td.bk-table-expanded-cell {
    background: #f5f7fa;
    padding: 0;
  }

  .fright-last{
    padding: 16px;
    background: #fafcfe;
    border: 1px solid #DCDEE5;
    min-width: 254px;
    h3 {
      font-weight: 700;
      font-size: 12px;
      color: #63656E;
      height: 32px;
      line-height: 32px;
    }
  }
  .dynamic-list li {
    padding-bottom: 5px;
    padding-left: 20px;
    position: relative;
  }
  .dynamic-list li:before {
    position: absolute;
    content: "";
    width: 10px;
    height: 10px;
    top: 3px;
    left: 1px;
    border: solid 1px rgba(87, 163, 241, 1);
    border-radius: 50%;
  }
  .dynamic-list li:after {
    position: absolute;
    content: "";
    width: 1px;
    height: 40px;
    top: 15px;
    left: 6px;
  }
  .dynamic-list li:before {
    border: solid 2px #D8D8D8;
  }
  .dynamic-list li:after {
    background: #D8D8D8;
  }
  .dynamic-list li:last-child:before {
    border: solid 2px #D8D8D8;
  }
  .dynamic-list li:last-child:after {
    background: transparent;
  }
  .dynamic-time {
    line-height: 18px;
    font-size: 12px;
    color: #979BA5;
    cursor: default;
    margin-top: 5px;
  }
  .dynamic-content {
    font-size: 14px;
    display: flex;
    flex-direction: column;
    height: 48px;
    overflow: hidden;
    color: #63656e;
  }
}
.module-select-custom {
  /deep/ i.paasng-project {
    color: #a3c5fd;
  }
}
</style>
