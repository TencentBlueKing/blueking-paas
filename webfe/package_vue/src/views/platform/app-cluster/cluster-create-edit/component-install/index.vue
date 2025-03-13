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
      <bk-exception
        v-if="!requiredComponents.length"
        class="exception-wrap-item exception-part"
        type="empty"
        scene="part"
      >
        {{ $t('暂无数据') }}
      </bk-exception>
      <template v-else>
        <ComponentManagement
          v-for="component in requiredComponents"
          :key="component.name"
          :component="component"
          :details="componentDetails[component.name]"
          :loading="componentLoadingStates[component.name]"
          :cluster-source="clusterDetails?.cluster_source"
          :cluster-id="clusterId"
          @show-detail="handleShowDetail"
          @show-values="handleShowValues"
          @show-edit="handleShowEdit"
          @polling="handlePollingDetail"
        />
      </template>
    </section>

    <section
      class="card-style ptional"
      :class="{ expand: isExpanded }"
      v-bkloading="{ isLoading, zIndex: 10 }"
    >
      <bk-collapse
        v-model="activeNames"
        ext-cls="ptional-components-cls"
      >
        <bk-collapse-item name="ptional-components">
          <div class="card-title">
            <i class="paasng-icon paasng-right-shape"></i>
            <span>{{ $t('可选组件') }}</span>
          </div>
          <bk-exception
            v-if="!optionalComponents.length"
            class="exception-wrap-item exception-part"
            type="empty"
            scene="part"
          >
            {{ $t('暂无数据') }}
          </bk-exception>
          <template v-else>
            <ComponentManagement
              slot="content"
              v-for="component in optionalComponents"
              :key="component.name"
              :component="component"
              :details="componentDetails[component.name]"
              :loading="componentLoadingStates[component.name]"
              :cluster-source="clusterDetails?.cluster_source"
              :cluster-id="clusterId"
              @show-detail="handleShowDetail"
              @show-values="handleShowValues"
              @show-edit="handleShowEdit"
              @polling="handlePollingDetail"
            />
          </template>
        </bk-collapse-item>
      </bk-collapse>
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
      @get-detail="getComponentDetail"
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
      // 必要组件
      requiredComponents: [],
      // 可选组件
      optionalComponents: [],
      curComponentName: '',
      // 集群详情
      clusterDetails: {},
      isShowDetail: false,
      isEditorSideslider: false,
      isShowComponentEdit: false,
      activeNames: ['ptional-components'],
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
    isExpanded() {
      return this.activeNames.length > 0;
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
        this.isLoading = false;
        this.requiredComponents = res.filter((v) => v.required);
        this.optionalComponents = res.filter((v) => !v.required);
        // 使用 Promise.all 并行获取组件详情，required 为必填项 必须安装成功才允许下一步
        const nextDisabled = res.some((v) => v.required && v.status !== 'installed');
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
        // 调用轮询函数获取组件详细信息
        await this.pollComponentDetail(componentName);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.setComponentLoadingState(componentName, false);
      }
    },
    async pollComponentDetail(componentName, conditionalFn = (ret) => ret.status === 'installing') {
      try {
        const ret = await this.$store.dispatch('tenant/getComponentDetail', {
          clusterName: this.clusterId,
          componentName,
        });
        this.$set(this.componentDetails, componentName, ret);
        // 如果组件的 status 是 'installing'，则在 5 秒后再次请求
        if (conditionalFn(ret)) {
          setTimeout(() => this.pollComponentDetail(componentName), 5000);
        }
      } catch (e) {
        if (e.status === 404) {
          return;
        }
        this.catchErrorHandler(e);
      }
    },

    // 更新、安装轮询当前组件详情
    handlePollingDetail(name) {
      this.pollComponentDetail(name, (ret) => {
        return !['installation_failed', 'installed'].includes(ret.status);
      });
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
    padding: 16px 24px;
    i {
      font-size: 12px;
      color: #4d4f56;
      transition: all 0.2s;
      margin-right: 6px;
      transform: translateY(-1px);
    }
    .card-title {
      margin-bottom: 32px;
    }
    &.ptional {
      margin-top: 16px;
      .card-title {
        margin-bottom: 0;
      }
    }
    &.expand {
      .card-title {
        margin-bottom: 32px;
      }
      i {
        transform: rotate(90deg) translateX(-1px);
      }
    }
  }
  .ptional-components-cls {
    /deep/ .bk-collapse-item {
      .bk-collapse-item-header {
        padding: 0;
        height: auto !important;
        .fr {
          display: none;
        }
      }
      .bk-collapse-item-content {
        padding: 0 !important;
      }
    }
  }
}
</style>
