<template>
  <div class="component-install-container">
    <section
      class="card-style"
      v-bkloading="{ isLoading, zIndex: 10 }"
    >
      <div class="card-title">
        <span>{{ $t('必要组件') }}</span>
        <span class="sub-tip ml8">
          {{ $t('必须安装这些组件后，集群才能部署蓝鲸应用') }}
        </span>
      </div>
      <ComponentManagement
        v-for="component in componentList"
        :key="component.name"
        :component="component"
        :details="componentDetails[component.name]"
        :loading="componentLoadingStates[component.name]"
        :cluster-source="clusterDetails?.cluster_source"
        :cluster-id="clusterId"
        @show-detail="handleShowDetail"
        @show-values="handleShowValues"
        @show-edit="handleShowEdit"
      />
    </section>

    <!-- 查看 values 侧栏 -->
    <EditorSideslider
      :show.sync="isEditorSideslider"
      :title="$t('查看 Values')"
      :value="valuesJson"
      :read-only="true"
    />

    <!-- 查看组件详情侧栏 -->
    <DetailComponentsSideslider
      v-if="!isLoading"
      :show.sync="isShowDetail"
      :name="curComponentName"
      :detail-data="detailSidesliderData"
    />

    <!-- 组件配置编辑 -->
    <ConfigEditSideslider
      :show.sync="isShowComponentEdit"
      :name="curComponentName"
      :data="detailSidesliderData"
      :cluster-id="clusterId"
      @show-values="handleShowValues"
    />
  </div>
</template>

<script>
import ComponentManagement from './component-management.vue';
import DetailComponentsSideslider from '../../comps/detail-components-sideslider.vue';
import EditorSideslider from '@/components/editor-sideslider';
import ConfigEditSideslider from './config-edit-sideslider.vue';

export default {
  name: 'ComponentInstall',
  components: {
    ComponentManagement,
    EditorSideslider,
    DetailComponentsSideslider,
    ConfigEditSideslider,
  },
  props: {
    clusterId: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      isLoading: false,
      // 组件列表loading
      componentLoadingStates: {},
      // 组件列表详情
      componentDetails: {},
      // 组件列表
      componentList: [],
      curComponentName: '',
      // 集群详情
      clusterDetails: {},
      isShowDetail: false,
      isEditorSideslider: false,
      isShowComponentEdit: false,
    };
  },
  created() {
    this.init();
  },
  computed: {
    detailSidesliderData() {
      return this.componentDetails[this.curComponentName] ?? {};
    },
    values() {
      return this.detailSidesliderData?.values || {};
    },
    valuesJson() {
      return JSON.stringify(this.values, null, 2);
    },
  },
  methods: {
    init() {
      this.getClusterComponents();
      this.getClusterDetails();
    },
    // 查看详情侧栏
    handleShowDetail(name) {
      this.isShowDetail = true;
      this.curComponentName = name;
    },
    // 查看 Values 侧栏
    handleShowValues(name) {
      this.isEditorSideslider = true;
      this.curComponentName = name;
    },
    // 组件配置编辑侧栏
    handleShowEdit(name) {
      this.isShowComponentEdit = true;
      this.curComponentName = name;
    },
    // 获取集群详情
    async getClusterDetails() {
      this.contentLoading = true;
      try {
        const ret = await this.$store.dispatch('tenant/getClusterDetails', {
          clusterName: this.clusterId,
        });
        this.clusterDetails = ret;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.contentLoading = false;
      }
    },
    // 获取集群组件列表
    async getClusterComponents() {
      this.isLoading = true;
      try {
        const res = await this.$store.dispatch('tenant/getClusterComponents', { clusterName: this.clusterId });
        this.componentList = res;
        this.isLoading = false;
        // 使用 Promise.all 并行获取组件详情，required 为必填项 必须安装成功才允许下一步
        const nextDisabled = this.componentList.some((v) => v.required && v.status !== 'installed');
        this.$emit('change-next-btn', nextDisabled);
        await Promise.all(res.map((component) => this.getComponentDetail(component.name)));
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
      }
    },
    // 获取集群组件详情
    async getComponentDetail(componentName) {
      try {
        // 更加精准的加载状态，跟踪每个组件详情的加载，而不是全局状态
        this.setComponentLoadingState(componentName, true);
        const ret = await this.$store.dispatch('tenant/getComponentDetail', {
          clusterName: this.clusterId,
          componentName,
        });
        this.$set(this.componentDetails, componentName, ret);
        // 这里可以处理获取到的组件详情数据，比如更新到某个状态管理中
      } catch (e) {
        if (e.status === 404) {
          return;
        }
        this.catchErrorHandler(e);
      } finally {
        this.setComponentLoadingState(componentName, false);
      }
    },

    // 新增一个方法来专门设置组件详情的加载状态
    setComponentLoadingState(componentName, isLoading) {
      this.$set(this.componentLoadingStates, componentName, isLoading);
    },
  },
};
</script>

<style lang="scss" scoped>
.component-install-container {
  .card-style {
    min-height: 500px;
    padding: 16px 24px;
  }
}
</style>
