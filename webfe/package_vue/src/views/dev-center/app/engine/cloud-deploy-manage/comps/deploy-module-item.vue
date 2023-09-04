<template>
  <div class="deploy-module-item">
    <!-- 预览模式 / 详情模式 / 未部署 -->
    <section class="top-info-wrapper">
      <!-- 已部署 -->
      <div class="left-info">
        <div class="module">
          <i class="paasng-icon paasng-restore-screen"></i>
          <span class="name">{{moduleData.name}}</span>
          <i class="paasng-icon paasng-jump-link icon-cls-link" v-if="isDeploy" />
        </div>
        <template v-if="isDeploy">
          <div class="version">
            <span class="label">版本：</span>
            <span class="value">58239632</span>
          </div>
          <div class="line"></div>
          <div class="branch">
            <span class="label">分支：</span>
            <span class="value">xxxx</span>
          </div>
        </template>
        <template v-else>
          <div class="not-deployed">暂未部署</div>
        </template>
      </div>
      <div class="right-btn">
        <bk-button :theme="'primary'" class="mr10" size="small">
          部署
        </bk-button>
        <bk-button :theme="'default'" size="small" :disabled="!isDeploy">
          下架
        </bk-button>
      </div>
    </section>
    <!-- 内容 -->
    <section class="main" v-if="isDeploy">
      <!-- 详情表格 -->
      <deploy-detail v-show="isExpand" />
      <!-- 预览 -->
      <deploy-preview v-show="!isExpand" />
      <div class="operation-wrapper">
        <div
          class="btn"
          @click="handleChangePanel">
          {{ isExpand ? '收起' : '展开详情' }}
          <i class="paasng-icon paasng-ps-arrow-down" v-if="!isExpand"></i>
          <i class="paasng-icon paasng-ps-arrow-up" v-else></i>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import deployDetail from './deploy-detail.vue'
import deployPreview from './deploy-preview.vue'

export default {
  components: {
    deployDetail,
    deployPreview
  },

  props: {
    moduleData: {
      type: Object,
      default: () => {}
    }
  },

  data () {
    return {
      isExpand: true,
    }
  },

  computed: {
    // 是否部署
    isDeploy () {
      return this.moduleData.repo;
    }
  },

  created () {
    // this.isExpand = this.isDeploy;
  },

  methods: {
    handleChangePanel () {
      this.isExpand = !this.isExpand;
    }
  }
}
</script>

<style lang="scss" scoped>
.deploy-module-item {
  margin-top: 16px;
  .top-info-wrapper {
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-left: 12px;
    padding-right: 24px;
    background: #EAEBF0;
    border-radius: 2px 2px 0 0;

    .left-info {
      flex: 1;
      display: flex;
      color: #63656E;

      .module {
        margin-right: 30px;

        i {
          cursor: pointer;
        }

        .name {
          font-weight: 700;
          font-size: 14px;
          color: #313238;
          margin-left: 12px;
          margin-right: 10px;
        }

        .icon-cls-link {
          color: #3A84FF;
        }
      }

      .line {
        width: 1px;
        margin: 0 24px;
        background: #DCDEE5;
      }

      .version {
      }
    }
  }
  .main {
    background: #fff;
    box-shadow: 0 2px 4px 0 #0000001a, 0 2px 4px 0 #1919290d;
    border-radius: 0 0 2px 2px;
  }
  .operation-wrapper {
    display: flex;
    justify-content: center;
    padding-bottom: 12px;
    .btn {
      font-size: 12px;
      color: #3A84FF;
      cursor: pointer;
    }
  }
  .not-deployed {
    flex: 1;
    text-align: center;
    font-size: 12px;
    color: #979ba5;
  }
}
</style>