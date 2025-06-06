<template>
  <div class="cluster-create-edit">
    <!-- 步骤条/详情模式单步编辑不展示步骤条 -->
    <ProgressBar
      v-if="!isDetailSingleStepEdit"
      :cur-step="curStep"
      :steps="steps"
    />
    <SelectCluster
      v-if="curStep === 1"
      ref="selectCluster"
      :loading="detailsLoading"
      :cluster-data="clusterDetails"
      @get-detail="getClusterDetails"
    />
    <ComponentConfig
      v-else-if="curStep === 2"
      :cluster-id="queryClusterId"
      ref="componentConfig"
    />
    <ComponentInstall
      @change-next-btn="changeNextStepDisabled"
      :cluster-id="queryClusterId"
      v-else-if="curStep === 3"
    />
    <ClusterFeature
      v-else-if="curStep === 4"
      :cluster-id="queryClusterId"
      ref="clusterFeature"
    />
    <section class="submit-btn">
      <bk-button
        v-if="curStep > 1 && !isDetailSingleStepEdit"
        :theme="'default'"
        @click="setStep(curStep - 1)"
      >
        {{ $t('上一步') }}
      </bk-button>
      <!-- 组件安装阶段，需要将必要组件安装成功才允许下一步 -->
      <span v-bk-tooltips="{ content: disabledTips, disabled: !nextBtnDisabled }">
        <bk-button
          class="ml8"
          :theme="'primary'"
          :disabled="nextBtnDisabled"
          :loading="nextBtnLodaing"
          @click="handleSubmit"
        >
          <!-- 详情页单独编辑 -->
          <template v-if="isDetailSingleStepEdit">{{ $t('保存') }}</template>
          <!-- 按步骤新建/编辑 -->
          <template v-else>
            {{ curStep === 1 || curStep === steps.length ? $t('保存') : $t('下一步') }}
          </template>
        </bk-button>
      </span>
      <bk-button
        :theme="'default'"
        class="ml8"
        @click="back"
      >
        {{ $t('取消') }}
      </bk-button>
    </section>
  </div>
</template>

<script>
import SelectCluster from './select-cluster/index.vue';
import ProgressBar from './comps/progress-bar.vue';
import ComponentConfig from './component-config.vue';
import ComponentInstall from './component-install/index.vue';
import ClusterFeature from './cluster-feature';
export default {
  name: 'ClusterCreateEdit',
  components: {
    SelectCluster,
    ProgressBar,
    ComponentConfig,
    ComponentInstall,
    ClusterFeature,
  },
  data() {
    return {
      nextBtnLodaing: false,
      curStep: 1,
      steps: [
        { title: this.$t('选择集群'), icon: 1 },
        { title: this.$t('组件配置'), icon: 2 },
        { title: this.$t('组件安装'), icon: 3 },
        { title: this.$t('集群特性'), icon: 4 },
      ],
      nextStepDisabled: true,
      // 集群详情
      clusterDetails: {},
      detailsLoading: false,
    };
  },
  computed: {
    nextBtnDisabled() {
      if (this.curStep === 3) {
        // require为true的组件，必须是已安装状态
        return this.nextStepDisabled;
      }
      return false;
    },
    disabledTips() {
      if (this.curStep === 3) {
        return this.$t('请先将必要组件安装成功');
      }
      return '';
    },
    queryClusterId() {
      return this.$route.query?.id || '';
    },
    queryStep() {
      return this.$route.query?.step || 1;
    },
    // 是否为详情页单独编辑
    isDetailSingleStepEdit() {
      return this.$route.query?.alone || false;
    },
  },
  created() {
    if (this.queryStep) {
      this.curStep = Number(this.queryStep);
    }
  },
  methods: {
    changeNextStepDisabled(data) {
      this.nextStepDisabled = data;
    },
    // 返回集群列表
    back() {
      this.$router.push({
        name: 'platformAppCluster',
        query: {
          active: 'list',
          ...(this.isDetailSingleStepEdit ? { type: 'detail' } : {}),
        },
        params: {
          // 返回详情需要的集群id
          ...(this.isDetailSingleStepEdit ? { clusterId: this.queryClusterId } : {}),
        },
      });
    },
    setStep(step) {
      this.curStep = step;
      const { query } = this.$route;
      // 保留当前step
      this.$router.push({
        query: {
          ...query,
          step,
        },
      });
    },
    async handleSubmit() {
      switch (this.curStep) {
        case 1:
          // 选择集群
          this.validate('selectCluster', this.queryClusterId ? this.updateCluster : this.createCluster);
          break;
        case 2:
          // 组件配置
          this.validate('componentConfig', this.updateClusterDetails);
          break;
        case 3:
          this.setStep(4);
          break;
        case 4:
          // 集群特性
          this.validate('clusterFeature', this.updateClusterDetails);
          break;
        default:
          break;
      }
    },
    // 校验
    async validate(refName, cb) {
      try {
        // 表单校验
        await this.$refs[refName]?.formValidate();
        const ret = this.$refs[refName].getFormData();
        if (refName === 'componentConfig') {
          // 更新集群组件配置信息
          cb(ret, () => {
            this.$paasMessage({
              theme: 'success',
              message: this.$t('更新组件配置成功'),
            });
            this.getClustersStatus(this.queryClusterId);
            if (!this.isDetailSingleStepEdit) {
              this.setStep(3);
            } else {
              this.back();
            }
          });
        } else if (refName === 'clusterFeature') {
          // 更新集群特性
          cb(ret, () => {
            this.$paasMessage({
              theme: 'success',
              message: this.$t('集群添加成功'),
            });
            this.getClustersStatus(this.queryClusterId);
            // 返回集群列表
            this.back();
          });
        } else {
          cb && cb(ret);
        }
      } catch (e) {
        console.warn(e);
      }
    },
    showSuccessInfo(data) {
      const h = this.$createElement;
      this.$bkInfo({
        type: 'success',
        width: 480,
        maskClose: false,
        title: this.$t('集群添加成功'),
        okText: this.$t('继续配置'),
        cancelText: this.$t('离开（稍后配置）'),
        subHeader: h(
          'div',
          {
            class: ['cluster-success-info-cls'],
          },
          [
            h('p', { class: 'tip-text' }, this.$t('后续的配置：组件配置、组件安装、集群特性')),
            h('p', { class: 'tip-text' }, this.$t('支持在集群列表页面继续配置')),
          ]
        ),
        confirmFn: () => {
          // 集群新建完成，添加id参数
          this.$router.push({ query: { id: data?.name } });
          this.setStep(2);
        },
        cancelFn: () => {
          this.back();
        },
      });
    },
    // 新建集群
    async createCluster(data) {
      this.nextBtnLodaing = true;
      try {
        await this.$store.dispatch('tenant/createCluster', {
          data,
        });
        // 新建集群-成功后给出Info提示
        this.showSuccessInfo(data);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.nextBtnLodaing = false;
      }
    },
    // 编辑集群
    async updateCluster(data) {
      this.nextBtnLodaing = true;
      const params = {
        ...this.clusterDetails,
        ...data,
      };
      try {
        await this.$store.dispatch('tenant/updateCluster', {
          clusterName: this.queryClusterId,
          data: params,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('集群更新成功'),
        });
        this.getClustersStatus(this.queryClusterId);
        if (!this.isDetailSingleStepEdit) {
          this.setStep(2);
        } else {
          this.back();
        }
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.nextBtnLodaing = false;
      }
    },
    // 更新集群详情
    async updateClusterDetails(data, successCallback) {
      this.nextBtnLodaing = true;
      try {
        const ret = await this.$store.dispatch('tenant/updateCluster', {
          clusterName: this.queryClusterId,
          data,
        });
        successCallback(ret);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.nextBtnLodaing = false;
      }
    },
    // 获取集群详情
    async getClusterDetails() {
      this.detailsLoading = true;
      try {
        const ret = await this.$store.dispatch('tenant/getClusterDetails', {
          clusterName: this.queryClusterId,
        });
        this.clusterDetails = ret;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.detailsLoading = false;
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
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.cluster-success-info-cls {
  text-align: left;
  font-size: 14px;
  padding: 8px 16px;
  color: #4d4f56;
  background: #f5f6fa;
  border-radius: 2px;
  .tip-text {
    line-height: 22px;
  }
}
.cluster-create-edit {
  position: relative;
  padding: 24px;
  padding-bottom: 72px;
  .ml8 {
    margin-left: 8px;
  }
  .submit-btn {
    display: flex;
    align-items: center;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 48px;
    padding-left: 264px;
    background: #ffffff;
    z-index: 101;
    box-shadow: 0 -3px 4px 0 rgba(0, 0, 0, 0.03922);
  }
}
.card-style {
  padding: 16px 24px;
}
</style>
<style lang="scss">
.cluster-create-edit .card-style {
  .card-title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    line-height: 22px;
    margin-bottom: 18px;
    .sub-tip {
      font-weight: 400;
      font-size: 12px;
      color: #979ba5;
      line-height: 20px;
    }
  }
}
</style>
