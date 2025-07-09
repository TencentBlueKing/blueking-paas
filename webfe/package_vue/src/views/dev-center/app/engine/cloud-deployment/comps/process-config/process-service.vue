<template>
  <div class="process-service">
    <section :class="[isEdit ? 'edit-mode' : 'view-mode']">
      <div
        class="tools"
        v-if="isEdit"
      >
        <div class="left">
          <bk-button
            theme="primary"
            size="small"
            :outline="true"
            icon="plus"
            ext-cls="new-process"
            @click="$emit('add', null)"
          >
            {{ $t('新增') }}
          </bk-button>
        </div>
        <div class="right"></div>
      </div>
      <div class="process process-list">
        <!-- 判断主进程， 判断为主入口 -->
        <process-card
          v-for="(process, index) in data"
          class="item"
          :key="process.name"
          :name="process.name"
          :mode="mode"
          :active="process.name === active"
          :main="process.name === mainName"
          :start-service="!!process.services?.length"
          :del-icon-disabled="data.length === 1"
          @edit="$emit('edit', process.name, index)"
          @delete="handleDelete(process.name, index)"
          @click.native="handleChange(process.name, index)"
        />
      </div>
    </section>
  </div>
</template>

<script>
import processCard from './process-card.vue';
export default {
  name: 'PrcessService',
  components: {
    processCard,
  },
  props: {
    data: {
      type: Array,
      default: () => [],
    },
    activeData: {
      type: Object,
      default: () => {},
    },
    mode: {
      type: String,
      default: 'view',
    },
    active: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      processDialog: {
        visible: false,
        title: this.$t('新增'),
        loading: false,
      },
      mainName: '',
    };
  },
  computed: {
    isEdit() {
      return this.mode === 'edit';
    },
  },
  watch: {
    data(newValue) {
      // 外界更新当前name，需要重新获取主入口
      this.setMainEntryName(newValue);
    },
    deep: true,
  },
  mounted() {
    this.setMainEntryName(this.data);
  },
  methods: {
    setMainEntryName(list = []) {
      this.mainName = list.find((v) => this.isMainEntry(v.services))?.name;
    },
    handleChange(name, index) {
      this.$emit('change', name, index);
    },
    handleDelete(name, index) {
      // 最少存在一个进程
      if (this.data.length === 1) return;
      const h = this.$createElement;
      this.$bkInfo({
        title: this.$t('是否删除进程'),
        extCls: 'delete-process-cls',
        theme: 'danger',
        width: 480,
        okText: this.$t('删除'),
        subHeader: h('div', [
          h('p', [h('span', { class: ['label'] }, `${this.$t('进程')}：`), h('span', name)]),
          h('div', { class: ['tips'] }, this.$t('删除该进程后，进程内所有配置将会清空，请谨慎操作')),
        ]),
        confirmFn: () => {
          this.$emit('delete', name, index);
        },
      });
    },
    // 判断是否为主入口
    isMainEntry(services) {
      if (!services?.length) return false;
      return services.some((service) => ['bk/http', 'bk/grpc'].includes(service.exposed_type?.name));
    },
  },
};
</script>

<style lang="scss" scoped>
.process-service {
  padding: 0 24px;
  margin-bottom: 20px;
  .edit-mode {
    background: #f5f7fa;
    border-radius: 2px;
    .tools {
      display: flex;
      justify-content: space-between;
      align-items: center;
      height: 40px;
      padding: 0 16px;
      background: #fafbfd;
      border: 1px solid #dcdee5;
      border-radius: 2px 2px 0 0;
      .left {
        .new-process {
          .icon-plus {
            top: 0;
            min-width: 12px;
          }
        }
      }
    }
    .process {
      background: #f5f7fa;
      padding: 16px;
    }
  }
  .process-list {
    display: flex;
    flex-wrap: wrap; /* 允许换行 */
    gap: 8px; /* 设置间隔 */
  }
}
</style>
<style lang="scss">
.delete-process-cls .bk-info-box .bk-dialog-sub-header.has-sub {
  padding: 5px 30px 16px !important;
  font-size: 12px;
  color: #313238;
  .label,
  .tips {
    color: #63656e;
  }
  .tips {
    display: flex;
    align-items: center;
    padding: 0 12px;
    margin-top: 16px;
    height: 46px;
    background: #f5f6fa;
    border-radius: 2px;
  }
}
</style>
