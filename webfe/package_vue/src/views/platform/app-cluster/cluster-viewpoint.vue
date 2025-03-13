<template>
  <div class="tenant-viewpoint-container">
    <bk-table
      :data="displayClusterList"
      :outer-border="false"
      :header-border="false"
      v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
    >
      <bk-table-column
        :label="$t('集群名称')"
        prop="name"
        width="160"
        show-overflow-tooltip
        :render-header="$renderHeader"
      >
        <template slot-scope="{ row }">
          <a
            href="javascript:;"
            class="name-link"
            @click="$emit('toggle', { flag: true, name: row.name })"
          >
            {{ row.name }}
          </a>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="`${$t('集群')} ID`"
        prop="bcs_cluster_id"
        width="130"
        show-overflow-tooltip
      >
        <template slot-scope="{ row }">{{ row.bcs_cluster_id || '--' }}</template>
      </bk-table-column>
      <bk-table-column
        :label="$t('描述')"
        prop="description"
        show-overflow-tooltip
      ></bk-table-column>
      <bk-table-column
        :label="$t('可用租户')"
        prop="availableTenants"
        class-name="tags-wrapper-cls tenant-column"
        column-key="available-tenant"
        :render-header="$renderHeader"
      >
        <template slot-scope="{ row }">
          <div
            v-if="row.availableTenants.length"
            class="available-tenants-tags"
          >
            <span
              v-for="(item, index) in row.availableTenants.slice(
                0,
                row.availableTenantTagIndex < 0 ? 0 : row.availableTenantTagIndex
              )"
              class="border-tag"
              :key="item"
            >
              {{ item }}
            </span>
            <span
              v-if="row.availableTenants.length - row.availableTenantTagIndex > 0"
              class="hidden-count"
              v-bk-tooltips="row.availableTenants.slice(row.availableTenantTagIndex).join('，')"
            >
              +{{
                row.availableTenantTagIndex < 0
                  ? row.availableTenants.length
                  : row.availableTenants.length - row.availableTenantTagIndex
              }}
            </span>
          </div>
          <span v-else>--</span>
        </template>
      </bk-table-column>
      <!-- 新增特性列 -->
      <bk-table-column
        :label="$t('特性')"
        prop="feature"
        class-name="tags-wrapper-cls feature-column"
        column-key="feature"
      >
        <template slot-scope="{ row }">
          <div
            v-if="row.feature.length"
            class="feature-tags no-border"
          >
            <span
              v-for="(item, index) in row.feature.slice(0, row.featureTagIndex < 0 ? 0 : row.featureTagIndex)"
              class="border-tag"
              :key="item"
            >
              {{ item }}
            </span>
            <span
              v-if="row.feature.length - row.featureTagIndex > 0"
              class="hidden-count"
              v-bk-tooltips="row.feature.slice(row.featureTagIndex).join('，')"
            >
              +{{ row.featureTagIndex < 0 ? row.feature.length : row.feature.length - row.featureTagIndex }}
            </span>
          </div>
          <span v-else>--</span>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('节点')"
        :width="80"
        prop="nodes"
      >
        <template slot-scope="{ row }">
          <span
            class="nodes"
            v-bk-tooltips="{
              content: row.nodes.join(),
              html: row.nodes.join('<br/>'),
              allowHTML: true,
            }"
          >
            {{ row.nodes.length }}
          </span>
          <i
            v-if="row.nodes.length"
            class="paasng-icon paasng-general-copy"
            v-copy="row.nodes.join('\n')"
          ></i>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('操作')"
        :width="localLanguage === 'en' ? 200 : 160"
      >
        <template slot-scope="{ row }">
          <bk-button
            theme="primary"
            text
            class="mr10"
            @click="editCluter(row)"
          >
            {{ $t('编辑') }}
          </bk-button>
          <bk-popconfirm
            width="276"
            trigger="click"
            @confirm="syncNodes(row)"
          >
            <div
              slot="content"
              class="sync-nodes-popconfirm"
            >
              <div class="title">{{ $t('确认同步节点？') }}</div>
              <div class="content-custom">
                <p class="name">
                  {{ $t('集群名称') }}：
                  <span class="n">{{ syncNodeName }}</span>
                </p>
                <div>{{ $t('同步集群节点到开发者中心，以便应用开启出口 IP 时能绑定到集群所有节点上。') }}</div>
              </div>
            </div>
            <bk-button
              theme="primary"
              text
              class="mr10"
              @click="syncNodeName = row.name"
            >
              {{ $t('同步节点') }}
            </bk-button>
          </bk-popconfirm>
          <bk-button
            theme="primary"
            text
            @click="handleDeleteCluster(row)"
          >
            {{ $t('删除') }}
          </bk-button>
        </template>
      </bk-table-column>
    </bk-table>

    <DeleteClusterDialog
      :show.sync="delDilaogConfig.isShow"
      :config="delDilaogConfig"
      @refresh="getClusterList"
    />
  </div>
</template>

<script>
import i18n from '@/language/i18n.js';
import DeleteClusterDialog from './comps/delete-cluster-dialog.vue';

export default {
  name: 'TenantViewpoint',
  components: {
    DeleteClusterDialog,
  },
  data() {
    return {
      isTableLoading: false,
      tenantList: [],
      displayClusterList: [],
      resizeObserver: null,
      syncNodeName: '',
      allocationState: {},
      delDilaogConfig: {
        isShow: false,
        row: {},
      },
    };
  },
  computed: {
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  created() {
    this.init();
  },
  beforeDestroy() {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }
  },
  methods: {
    init() {
      this.getClusterList();
    },
    // 字段模糊搜索
    fuzzySearch(searchTerm) {
      const lowerCaseSearchTerm = searchTerm.toLocaleLowerCase();
      // 过滤数据，检查 name 和 bcs_cluster_id 是否包含搜索词
      this.displayClusterList = this.tenantList.filter((item) => {
        const nameMatches = item.name && item.name.toLocaleLowerCase().includes(lowerCaseSearchTerm);
        const clusterIdMatches =
          item.bcs_cluster_id && item.bcs_cluster_id.toLocaleLowerCase().includes(lowerCaseSearchTerm);
        return nameMatches || clusterIdMatches;
      });
    },
    // 获取集群列表
    async getClusterList() {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('tenant/getClusterList');
        this.tenantList = res.map((item) => {
          return {
            ...item,
            availableTenants: item.available_tenants,
            feature: item.feature_flags,
            availableTenantTagIndex: 0,
            featureTagIndex: 0,
          };
        });
        this.displayClusterList = this.tenantList;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        setTimeout(() => {
          this.isTableLoading = false;
          this.calculateVisibleTags();
          this.handleResizeObserver();
        }, 100);
      }
    },
    // 同步节点确认
    async syncNodes(row) {
      try {
        await this.$store.dispatch('tenant/syncNodes', {
          clusterName: row.name,
        });
        this.getClusterList();
        this.$paasMessage({
          theme: 'success',
          message: this.$t('同步成功！'),
        });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取集群使用情况
    async getClusterAllocationState(name) {
      try {
        const ret = await this.$store.dispatch('tenant/getClusterAllocationState', {
          clusterName: name,
        });
        this.allocationState = ret;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    async handleDeleteCluster(row) {
      await this.getClusterAllocationState(row.name);
      if (!!(this.allocationState.bound_app_module_envs?.length || this.allocationState.allocated_tenant_ids?.length)) {
        // 无法删除集群
        this.showDelAlertInfo(this.allocationState, row.name);
      } else {
        // 删除集群
        this.delDilaogConfig.isShow = true;
        this.delDilaogConfig.row = row;
      }
    },
    // 无法删除集群info提示
    showDelAlertInfo(data, name) {
      const h = this.$createElement;
      this.$bkInfo({
        width: 480,
        type: 'warning',
        extCls: 'cluster-alert-info-cls',
        title: this.$t('无法删除集群'),
        subHeader: h('div', { class: 'del-alert-info-content' }, [
          h('div', { class: 'sub-info' }, `${i18n.t('集群（{n}）正在被以下租户、应用使用，无法删除', { n: name })}：`),
          h('div', [
            `1. ${i18n.t('被')}`,
            ...data.available_tenant_ids.slice(0, 2).map((item) => h('span', { class: 'tag' }, item)),
            i18n.t('等'),
            h('span', { class: 'count' }, data.available_tenant_ids.length),
            i18n.t('个租户使用，请先在集群配置页面，解除租户与集群的分配关系。'),
          ]),
          h('div', [
            `2. ${i18n.t('Bound-by')}`,
            h('span', { class: 'count' }, data.bound_app_module_envs.length),
            h('i', {
              class: `paasng-icon paasng-general-copy ${!data.bound_app_module_envs.length ? 'hide' : ''}`,
              directives: [
                {
                  name: 'copy',
                  value: JSON.stringify(data.bound_app_module_envs, null, 2),
                },
              ],
            }),
            i18n.t('个应用模块绑定'),
          ]),
        ]),
        maskClose: true,
      });
    },
    handleResizeObserver() {
      this.$nextTick(() => {
        this.resizeObserver = new ResizeObserver((entries) => {
          this.calculateVisibleTags();
        });
        const tenantColumn = document.querySelector('.tenant-column');
        const featureColumn = document.querySelector('.feature-column');
        if (tenantColumn === null || featureColumn === null) {
          return;
        }
        this.resizeObserver.observe(tenantColumn);
        this.resizeObserver.observe(featureColumn);
      });
    },
    // 计算当前td可展示的tags
    calculateVisibleTags() {
      this.$nextTick(() => {
        const tenantParentDom = document.querySelector('.available-tenants-tags');
        const featureParentDom = document.querySelector('.feature-tags');
        const pageDom = document.querySelector('.tenant-viewpoint-container');
        if (tenantParentDom === null || featureParentDom === null || pageDom === null) {
          return;
        }
        const { width: tenantParentWidth } = tenantParentDom.getBoundingClientRect();
        const { width: featureParentWidth } = featureParentDom.getBoundingClientRect();

        this.tenantList.forEach((item) => {
          item.availableTenantTagIndex = this.calculateTagIndex(item.availableTenants, tenantParentWidth, pageDom);
          item.featureTagIndex = this.calculateTagIndex(item.feature, featureParentWidth, pageDom);
        });
      });
    },
    calculateTagIndex(tags, parentWidth, parentDom) {
      let remainWidth = parentWidth;
      const findVisibleTags = (index, isBack) => {
        if (index < 0) {
          return 0;
        }

        const tagWidth = this.createTagDom(tags[index], parentDom);

        if (isBack) {
          const foldTagWidth = this.createTagDom(`+${tags.length - index}`, parentDom);
          if (foldTagWidth > remainWidth + tagWidth) {
            return findVisibleTags(index - 1, true);
          }
          return index;
        }

        if (tagWidth > remainWidth) {
          const foldTagWidth = this.createTagDom(`+${tags.length - index}`, parentDom);
          if (foldTagWidth > remainWidth) {
            return findVisibleTags(index - 1, true);
          }
        } else {
          remainWidth -= tagWidth;
          return findVisibleTags(index + 1);
        }
        return index;
      };
      return findVisibleTags(0);
    },
    createTagDom(val, parentDom) {
      const tagDom = document.createElement('span');
      parentDom.appendChild(tagDom);
      tagDom.innerText = val;
      tagDom.classList.add('border-tag');
      tagDom.style.position = 'absolute';
      tagDom.style.opacity = 0;
      const { width } = tagDom.getBoundingClientRect();
      parentDom.removeChild(tagDom);
      return width;
    },
    editCluter(row) {
      this.$router.push({
        name: 'clusterCreateEdit',
        params: {
          type: 'edit',
        },
        query: {
          id: row.name,
          step: 1,
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.tenant-viewpoint-container {
  margin-top: 16px;
  .name-link {
    display: inline-block;
    width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .nodes {
    padding: 0 5px;
  }
  .paasng-general-copy {
    display: none;
    color: #3a84ff;
    cursor: pointer;
  }
  /deep/ .bk-table-row.hover-row .paasng-general-copy {
    display: inline-block;
  }
  /deep/ .tags-wrapper-cls {
    .cell {
      display: flex;
      align-items: center;
    }
  }
  /deep/ td.tenant-column-cls,
  /deep/ td.feature-column-cls {
    background: #f5f7fa;
    border-right: 1px solid #dcdee5;
  }
  .hidden-count {
    flex-shrink: 0;
    display: inline-block;
    height: 22px;
    line-height: 22px;
    font-size: 12px;
    color: #4d4f56;
    padding: 0 8px;
    border-radius: 2px;
    background: #fafbfd;
    border: 1px solid #dcdee5;
  }
  .available-tenants-tags,
  .feature-tags {
    width: 100%;
    display: flex;
    &.no-border {
      .border-tag,
      .hidden-count {
        border: none;
        background: #f0f1f5;
      }
    }
    .border-tag {
      flex-shrink: 0;
      margin-right: 4px;
      &:last-child {
        margin-right: 0;
      }
    }
  }
}
.sync-nodes-popconfirm {
  margin-bottom: 16px;
  font-size: 12px;
  color: #4d4f56;
  line-height: 20px;
  .title {
    line-height: 24px;
    font-size: 16px !important;
  }
  .content-custom {
    line-height: 20px;
  }
  .name {
    margin-bottom: 4px;
    .n {
      color: #313238;
    }
  }
}
.del-alert-info-content {
  text-align: left;
  padding: 12px 16px;
  font-size: 12px;
  border-radius: 2px;
  line-height: 22px;
  color: #4d4f56;
  background: #f5f6fa;
  .sub-info {
    margin-bottom: 8px;
  }
  .tag {
    display: inline-block;
    height: 22px;
    line-height: 22px;
    padding: 0 8px;
    background: #fafbfd;
    border: 1px solid #dcdee5;
    border-radius: 2px;
    margin-right: 4px;
    &:last-child {
      margin-right: 0;
    }
    &:first-child {
      margin-left: 4px;
    }
  }
  .count {
    color: #eb3131;
    font-weight: 700;
    padding: 0 3px;
  }
  i {
    color: #3a84ff;
    cursor: pointer;
  }
}
</style>
<style>
.cluster-alert-info-cls .bk-dialog-footer button:first-child {
  display: none;
}
</style>
