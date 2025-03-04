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
      />
      <!-- 二期租户视角 -->
    </div>
    <ClusterDetails
      v-else
      :active="curClusterDetailName"
      @toggle="handleToggleDetails"
    />
  </div>
</template>

<script>
import ClusterViewpoint from './cluster-viewpoint.vue';
import ClusterDetails from './comps/cluster-details.vue';
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
      curClusterDetailName: '',
    };
  },
  computed: {
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
        this.curClusterDetailName = data.name;
        newQuery.type = 'detail';
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
