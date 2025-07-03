<template>
  <div class="node-info-container">
    <div class="top-btns">
      <bk-popconfirm
        trigger="click"
        width="288"
        placement="bottom-start"
        ext-cls="sync-node-popper-cls"
        @confirm="handleSyncNode"
      >
        <div slot="content">
          <div class="popconfirm-title mb-16">{{ $t('确认同步节点？') }}</div>
          <div class="content">
            <p class="name">
              {{ $t('集群名称') }}：
              <span style="color: #313238">{{ clusterName }}</span>
            </p>
            <p class="mt-4">{{ $t('同步集群节点到开发者中心，以便应用开启出口 IP 时能绑定到集群所有节点上。') }}</p>
          </div>
        </div>
        <bk-button
          theme="primary"
          :outline="true"
        >
          {{ $t('同步节点') }}
        </bk-button>
      </bk-popconfirm>
      <bk-button
        :theme="'default'"
        class="ml-12"
        @click="viewSyncRecords"
      >
        {{ $t('查看同步记录') }}
      </bk-button>
    </div>
    <section class="mt-24">
      <DetailsRow
        v-for="(val, key) in nodeKeys"
        :align="'flex-start'"
        :label-width="localLanguage === 'en' ? 150 : 100"
        :key="key"
      >
        <template slot="label">{{ `${val}：` }}</template>
        <template slot="value">
          <template v-if="key === 'createdAt'">{{ nodeDetail[key] || '--' }}</template>
          <div
            class="node-lsit"
            v-else
          >
            <!-- 节点信息 -->
            <span v-if="!nodeDetail[key]?.length">--</span>
            <template v-else>
              <template v-if="key === 'nodes'">
                <section>
                  <div
                    v-for="node in nodeDetail[key]"
                    :key="node"
                  >
                    {{ node }}
                  </div>
                </section>
              </template>
              <div
                v-else
                class="apps"
                v-bk-overflow-tips
              >
                <span>{{ nodeDetail[key]?.join(' / ') || '' }}</span>
              </div>
              <i
                v-bk-tooltips="$t('复制')"
                class="paasng-icon paasng-general-copy"
                v-copy="nodeDetail[key]"
              ></i>
            </template>
          </div>
        </template>
      </DetailsRow>
    </section>

    <!-- 同步记录 -->
    <bk-sideslider
      :is-show.sync="sideConfig.isShow"
      :quick-close="true"
      :title="$t('节点同步记录')"
      :width="960"
    >
      <div
        class="sync-records-container"
        slot="content"
      >
        <bk-table
          :data="syncRecords"
          v-bkloading="{ isLoading: sideConfig.loading, zIndex: 10 }"
          size="large"
          ext-cls="sync-records-table-cls"
        >
          <bk-table-column
            :label="$t('同步时间')"
            prop="createdAt"
            width="120"
            :render-header="$renderHeader"
          ></bk-table-column>
          <bk-table-column
            :label="$t('节点数')"
            prop="nodeCount"
            width="100"
            :render-header="$renderHeader"
          ></bk-table-column>
          <bk-table-column
            :label="$t('节点信息')"
            :show-overflow-tooltip="true"
          >
            <template slot-scope="{ row }">
              <section class="info node-info">
                <div
                  v-for="node in row.nodes"
                  :key="node"
                  class="node-width"
                  v-bk-overflow-tips
                >
                  {{ node }}
                </div>
                <i
                  class="paasng-icon paasng-general-copy copy-icon"
                  v-copy="row.nodes"
                />
              </section>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('绑定应用')"
            :show-overflow-tooltip="true"
          >
            <template slot-scope="{ row }">
              <div
                class="info"
                v-if="row.binding_apps.length"
              >
                <div class="apps">{{ row.binding_apps?.join(' / ') }}</div>
                <i
                  class="paasng-icon paasng-general-copy copy-icon"
                  v-copy="row.binding_apps"
                />
              </div>
              <span v-else>--</span>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
import DetailsRow from '@/components/details-row';
import { mapState } from 'vuex';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

export default {
  name: 'NodeInfo',
  components: {
    DetailsRow,
  },
  props: {
    clusterName: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      nodeKeys: {
        nodes: this.$t('节点信息'),
        binding_apps: this.$t('绑定应用'),
        createdAt: this.$t('同步时间'),
      },
      nodeDetail: {},
      sideConfig: {
        isShow: false,
        loading: false,
      },
      syncRecords: [],
    };
  },
  computed: {
    ...mapState(['localLanguage']),
  },
  created() {
    dayjs.extend(relativeTime);
    if (this.localLanguage !== 'en') {
      dayjs.locale('zh-cn');
    }
    this.getNodesState();
  },
  methods: {
    // 获取节点信息
    async getNodesState() {
      this.nodeDetail = {};
      try {
        const ret = await this.$store.dispatch('tenant/getNodesState', {
          clusterName: this.clusterName,
        });
        this.nodeDetail = {
          ...ret,
          createdAt: dayjs(ret.created_at).fromNow(),
        };
      } catch (e) {
        if (e.status === 404) {
          this.nodeDetail = {};
          return;
        }
        this.catchErrorHandler(e);
      }
    },
    // 获取节点同步记录
    async getNodesSyncRecords() {
      try {
        this.sideConfig.loading = true;
        const res = await this.$store.dispatch('tenant/getNodesSyncRecords', {
          clusterName: this.clusterName,
        });
        this.syncRecords = res.map((v) => ({
          ...v,
          createdAt: dayjs(v.created_at).fromNow(),
          nodeCount: v.nodes?.length || 0,
        }));
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.sideConfig.loading = false;
      }
    },
    viewSyncRecords() {
      this.sideConfig.isShow = true;
      this.getNodesSyncRecords();
    },
    // 确认同步节点
    async handleSyncNode() {
      try {
        await this.$store.dispatch('tenant/syncNodes', {
          clusterName: this.clusterName,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('同步成功！'),
        });
        this.getNodesState();
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.node-info-container {
  .node-lsit {
    position: relative;
    padding-right: 22px;
    .paasng-general-copy {
      position: absolute;
      right: 0px;
      top: 10px;
    }
  }
  i.paasng-general-copy {
    color: #3a84ff;
    cursor: pointer;
  }
  .apps {
    white-space: pre-wrap;
    display: -webkit-box;
    overflow: hidden;
    text-overflow: ellipsis;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3; /* 限制显示的行数 */
  }
}
.sync-records-container {
  padding: 24px 40px;
  .sync-records-table-cls {
    /deep/ .bk-table-row.hover-row {
      .copy-icon {
        display: block;
      }
    }
  }
  .node-info {
    padding: 5px 0;
  }
  .info {
    width: calc(100% - 30px);
    color: #4d4f56;
    overflow: hidden;
    line-height: 20px;
    .node-list-wrapper {
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
    }
    .node-width {
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
    }
    .copy-icon {
      display: none;
      position: absolute;
      right: 20px;
      top: 50%;
      transform: translateY(-50%);
    }
  }
}
.sync-node-popper-cls {
  .popconfirm-title {
    font-size: 16px;
    color: #313238;
    line-height: 24px;
  }
  .content {
    font-size: 12px;
    color: #4d4f56;
    line-height: 20px;
  }
}
</style>
