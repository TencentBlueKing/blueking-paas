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
          :btn-loading="componentBtnLoadings[component.name]"
          :cluster-source="clusterDetails?.cluster_source"
          :cluster-id="clusterId"
          @show-detail="handleShowDetail"
          @show-values="handleShowValues"
          @show-edit="handleShowEdit"
          @polling="pollingDetail"
          @change-status="changeComponentStatus"
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
              :btn-loading="componentBtnLoadings[component.name]"
              :cluster-source="clusterDetails?.cluster_source"
              :cluster-id="clusterId"
              @show-detail="handleShowDetail"
              @show-values="handleShowValues"
              @show-edit="handleShowEdit"
              @polling="pollingDetail"
              @change-status="changeComponentStatus"
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
      @update-config="updateNginxComponentValues"
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
      // 组件安装/更新按钮loading
      componentBtnLoadings: {},
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
        // 必要组件指定规则
        const requiredOrder = ['bk-ingress-nginx', 'bkpaas-app-operator', 'bkapp-log-collection'];
        // 必要组件排序
        this.requiredComponents = res
          .filter((v) => v.required)
          .sort((a, b) => {
            const indexA = requiredOrder.indexOf(a.name);
            const indexB = requiredOrder.indexOf(b.name);
            return (indexA === -1 ? Infinity : indexA) - (indexB === -1 ? Infinity : indexB);
          });
        // 其他组件按字母排序
        this.optionalComponents = res.filter((v) => !v.required).sort((a, b) => a.name.localeCompare(b.name));
        // 使用 Promise.all 并行获取组件详情，required 为必填项 必须安装成功才允许下一步
        const nextDisabled = res.some((v) => v.required && v.status !== 'installed');
        this.$emit('change-next-btn', nextDisabled);
        // 关闭容器Loading
        this.isLoading = false;
        await Promise.all(res.map((component) => this.getComponentDetail(component.name)));
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
      }
    },

    // 本地更新状态组件状态
    changeComponentStatus(componentName, status) {
      const data = this.componentDetails[componentName];
      this.$set(this.componentDetails, componentName, {
        ...data,
        status,
      });
    },

    // 直接获取组件详情调用
    async getComponentDetail(componentName, isPoll = false) {
      try {
        // 开启组件区域 loading
        if (!isPoll) {
          // 轮询状态无需开启lodaing
          this.setComponentLoadingState(componentName, true);
        }
        const ret = await this.$store.dispatch('tenant/getComponentDetail', {
          clusterName: this.clusterId,
          componentName,
        });
        this.$set(this.componentDetails, componentName, ret);

        // 状态为 installing 轮询接口
        if (ret.status === 'installing') {
          setTimeout(() => {
            this.getComponentDetail(componentName, true);
          }, 5000);
        }
      } catch (e) {
        if (e.status === 404) {
          // 未安装接口为404
          this.$set(this.componentDetails, componentName, {
            status: 'not_installed',
          });
          return;
        }
        this.catchErrorHandler(e);
      } finally {
        this.setComponentLoadingState(componentName, false);
      }
    },

    // 更新、安装操作时调用
    async pollingDetail(componentName) {
      try {
        // 开启按钮安装/更新loading
        this.$set(this.componentBtnLoadings, componentName, true);
        const ret = await this.$store.dispatch('tenant/getComponentDetail', {
          clusterName: this.clusterId,
          componentName,
        });
        this.$set(this.componentDetails, componentName, ret);
        if (['installation_failed', 'installed'].includes(ret.status)) {
          // 结束轮询
          this.$set(this.componentBtnLoadings, componentName, false);
        } else {
          setTimeout(() => {
            this.pollingDetail(componentName);
          }, 5000);
        }
      } catch (e) {
        if (e.status === 404) {
          this.$set(this.componentDetails, componentName, {
            status: 'not_installed',
          });
          setTimeout(() => {
            this.pollingDetail(componentName);
          }, 5000);
          return;
        }
        // 其他错误情况关闭Loading
        this.$set(this.componentBtnLoadings, componentName, false);
        this.catchErrorHandler(e);
      }
    },

    // 新增一个方法来专门设置组件详情的加载状态
    setComponentLoadingState(componentName, isLoading) {
      this.$set(this.componentLoadingStates, componentName, isLoading);
    },
    // 更新bk-ingress-nginx组件配置
    updateNginxComponentValues(values) {
      const config = Object.assign(this.componentDetails['bk-ingress-nginx'], values);
      this.$set(this.componentDetails, 'bk-ingress-nginx', config);
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
