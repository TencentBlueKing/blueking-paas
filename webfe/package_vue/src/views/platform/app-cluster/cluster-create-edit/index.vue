<template>
  <div class="cluster-create-edit">
    <!-- 步骤条 -->
    <ProgressBar :cur-step="curStep" />
    <SelectCluster
      v-if="curStep === 1"
      ref="selectCluster"
    />
    <ComponentConfig
      v-else-if="curStep === 2"
      :cluster-id="clusterId"
      ref="componentConfig"
    />
    <ComponentInstall v-else-if="curStep === 3" />
    <section class="submit-btn">
      <bk-button
        v-if="curStep > 1"
        :theme="'default'"
        @click="setStep(curStep - 1)"
      >
        {{ $t('上一步') }}
      </bk-button>
      <bk-button
        class="ml8"
        :theme="'primary'"
        :loading="nextBtnLodaing"
        @click="handleSubmit"
      >
        {{ curStep === 1 ? $t('保存并下一步') : $t('下一步') }}
      </bk-button>
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
export default {
  name: 'ClusterCreateEdit',
  components: {
    SelectCluster,
    ProgressBar,
    ComponentConfig,
    ComponentInstall,
  },
  data() {
    return {
      nextBtnLodaing: false,
      curStep: 3,
      // 暂时未固定值 paas-test 测试集群id，后续替换新建、编辑集群id
      clusterId: 'paas-test',
    };
  },
  methods: {
    // 返回集群列表
    back() {
      this.$router.push({
        name: 'platformAppCluster',
        query: {
          active: 'list',
        },
      });
    },
    setStep(step) {
      this.curStep = step;
    },
    async handleSubmit() {
      switch (this.curStep) {
        case 1:
          this.validate('selectCluster', this.createCluster);
          break;
        case 2:
          this.validate('componentConfig', this.updataComponentConfig);
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
        cb && cb(ret);
      } catch (e) {
        console.warn(e);
      }
    },
    // 新建集群
    async createCluster(data) {
      this.nextBtnLodaing = true;
      try {
        const ret = await this.$store.dispatch('tenant/createCluster', {
          data,
        });
        // 返回新建集群ID
        // this.clusterId = ret;
        console.log(ret);
        this.$paasMessage({
          theme: 'success',
          message: this.$t('新建成功'),
        });
        this.setStep(2);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.nextBtnLodaing = false;
      }
    },
    // 更新集群组件配置信息
    async updataComponentConfig(data) {
      this.nextBtnLodaing = true;
      try {
        const ret = await this.$store.dispatch('tenant/updateCluster', {
          clusterName: this.clusterId,
          data,
        });
        console.log(ret);
        this.$paasMessage({
          theme: 'success',
          message: this.$t('更新组件配置成功'),
        });
        this.setStep(3);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.nextBtnLodaing = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
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
