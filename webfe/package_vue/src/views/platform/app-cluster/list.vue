<template>
  <div class="cluster-list-container">
    <bk-alert
      type="warning"
      :title="$t('若执行集群扩缩容操作，请及时执行 “同步节点” 操作来更新集群节点状态。')"
    ></bk-alert>
    <div
      class="cluster-list card-style"
      v-if="!isExpandDetails"
    >
      <!-- 集群列表 -->
      <div class="top-tool">
        <div class="left flex-row">
          <bk-button
            :theme="'primary'"
            @click="addCluter"
          >
            {{ $t('添加集群') }}
          </bk-button>
          <!-- 二期视角切换 -->
        </div>
        <bk-input
          v-model="searchValue"
          :placeholder="$t('搜索集群名称、集群ID')"
          :right-icon="'bk-icon icon-search'"
          style="width: 480px"
          clearable
          @input="handleSearch"
        ></bk-input>
      </div>
      <ClusterViewpoint
        v-if="buttonActive === 'cluster'"
        ref="clusterRef"
        @toggle="handleToggleDetails"
        @get-status="getClusterListStatus"
      />
      <!-- 二期租户视角 -->
    </div>
    <ClusterDetails
      v-else
      @toggle="handleToggleDetails"
      @get-status="getClusterListStatus"
    />
  </div>
</template>

<script>
import ClusterViewpoint from './cluster-viewpoint.vue';
import ClusterDetails from './comps/cluster-details.vue';
import { mapState } from 'vuex';
export default {
  name: 'ClusterList',
  components: {
    ClusterViewpoint,
    ClusterDetails,
  },
  data() {
    return {
      buttonList: [
        { name: 'cluster', label: this.$t('集群视角'), icon: 'organization' },
        { name: 'tenant', label: this.$t('租户视角'), icon: 'user2' },
      ],
      buttonActive: 'cluster',
      searchValue: '',
    };
  },
  computed: {
    ...mapState('tenant', {
      clustersStatus: state => state.clustersStatus,
    }),
    isExpandDetails() {
      return this.$route.query?.type === 'detail';
    },
  },
  methods: {
    handlerChange(data) {
      this.buttonActive = data.name;
    },
    // 打开集群详情
    handleToggleDetails(data) {
      const { path, query } = this.$route;
      let newQuery = { ...query };
      if (typeof data === 'boolean') {
        newQuery = { active: query.active };
      } else {
        newQuery.type = 'detail';
        this.$store.commit('tenant/updateDetailActiveName', data.name);
      }
      this.$router.push({ path, query: newQuery });
    },
    // 前端搜索
    handleSearch() {
      this.$refs.clusterRef?.fuzzySearch(this.searchValue);
    },
    addCluter() {
      this.$router.push({
        name: 'clusterCreateEdit',
        params: {
          type: 'add',
        },
        query: {
          step: 1,
        },
      });
    },
    async getClusterListStatus(clusters) {
      // 判断是否已存入 state 中
      if (Object.keys(this.clustersStatus)?.length > 0) {
        return;
      }
      try {
        await Promise.allSettled(clusters.map(cluster => this.getClustersStatus(cluster.name).catch(() => null)));
      } catch (e) {
        console.error(e);
      }
    },
    // 获取集群状态
    async getClustersStatus(clusterName) {
      try {
        const ret = await this.$store.dispatch('tenant/getClustersStatus', {
          clusterName,
        });
        const hasIcon = !ret.basic || !ret.component || !ret.feature;
        this.$store.commit('tenant/updateClustersStatus', {
          clusterName,
          status: {
            ...ret,
            hasIcon,
          },
        });
      } catch (e) {
        this.catchErrorHandler(e);
        // 接口错误，统一为未配置
        this.$store.commit('tenant/updateClustersStatus', {
          clusterName,
          status: {
            basic: false,
            component: false,
            feature: false,
            hasIcon: true,
          },
        });
        throw e;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.cluster-list-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  .cluster-list {
    flex: 1;
    min-width: 0;
    margin-top: 16px;
    padding: 16px;
  }
  .top-tool {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .ml8 {
    margin-left: 8px;
  }
  .btn-icon {
    font-size: 12px;
    color: #979ba5;
  }
}
</style>
