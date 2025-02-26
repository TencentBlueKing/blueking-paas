<template>
  <div class="cluster-create-edit">
    <SelectCluster ref="selectCluster" />
    <section class="submit-btn">
      <bk-button
        :theme="'primary'"
        @click="handleSubmit"
      >
        {{ $t('保存并下一步') }}
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
import SelectCluster from './select-cluster.vue';
export default {
  name: '',
  components: {
    SelectCluster,
  },
  data() {
    return {
      nextBtnLodaing: false,
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
    async handleSubmit() {
      // 获取表单数据
      try {
        await this.$refs.selectCluster?.formValidate();
        const ret = this.$refs.selectCluster.getFormData();
        console.log('表单', ret);
        this.createCluster(ret);
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
        console.log(ret);
        this.$paasMessage({
          theme: 'success',
          message: this.$t('新建成功'),
        });
        this.back();
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
    box-shadow: 0 -3px 4px 0 rgba(0, 0, 0, 0.03922);
  }
}
</style>
