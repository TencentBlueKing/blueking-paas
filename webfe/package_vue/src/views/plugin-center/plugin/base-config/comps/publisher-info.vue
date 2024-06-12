<template>
  <div class="publisher-info card-style">
    <div class="title">
      {{ $t('发布者') }}
      <span class="tip">
        {{
          localLanguage === 'en'
            ? curPluginSchema.plugin_type?.description_en
            : curPluginSchema.plugin_type?.description_zh_cn
        }}
      </span>
    </div>
    <section class="main">
      <div class="editing-mode" v-if="isEdit">
        <user
          ref="memberSelectorRef"
          v-model="publisher"
          :placeholder="$t('请输入并按Enter结束')"
          :multiple="false"
          @change="handleChange"
        />
      </div>
      <template v-else>
        <div
          :class="curPluginInfo.publisher ? 'publisher-tag' : 'publisher-emp'"
          v-if="curPluginInfo.publisher"
        >
          {{ curPluginInfo.publisher || '' }}
          <i
            class="paasng-icon paasng-edit-2"
            @click="handleEdit"
          />
        </div>
        <p
          class="publisher-emp"
          v-else
        >
          {{ $t('请选择发布者') }}
          <i
            class="paasng-icon paasng-edit-2"
            @click="handleEdit"
          />
        </p>
      </template>
    </section>
  </div>
</template>

<script>
import User from '@/components/user';
import { bus } from '@/common/bus';
export default {
  name: 'PublisherInfo',
  components: {
    User,
  },
  data() {
    return {
      curPluginSchema: {},
      publisher: [],
      isEdit: false,
    };
  },
  computed: {
    pdId() {
      return this.$route.params.pluginTypeId;
    },
    pluginId() {
      return this.$route.params.id;
    },
    curPluginInfo() {
      return this.$store.state.plugin.curPluginInfo;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  created() {
    bus.$on('plugin-schemas', (data) => {
      this.curPluginSchema = data;
    });
  },
  methods: {
    handleEdit() {
      this.isEdit = true;
    },
    // 变更发布人
    async handleChange() {
      const publisher = this.publisher[0];
      try {
        await this.$store.dispatch('plugin/updatePublisher', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          data: {
            publisher,
          },
        });
        await this.$store.dispatch('plugin/getPluginInfo', { pluginId: this.pluginId, pluginTypeId: this.pdId });
        // 获取基本信息接口
        this.$paasMessage({
          theme: 'success',
          message: this.$t('保存成功！'),
        });
        this.isEdit = false;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.publisher-info {
  padding: 24px;
  .title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    line-height: 22px;
    .tip {
      margin-left: 10px;
      font-weight: 400;
      font-size: 12px;
      color: #979ba5;
      line-height: 20px;
    }
  }
  .main {
    margin-top: 16px;
    .editing-mode {
      width: 240px;
    }
    .publisher-tag {
      display: inline-block;
      height: 28px;
      line-height: 28px;
      padding: 0 12px;
      font-size: 12px;
      background: #f0f1f5;
      border-radius: 2px;
      color: #63656e;
    }
    .publisher-emp {
      font-size: 12px;
      color: #c4c6cc;
    }
    i.paasng-edit-2 {
      color: #3a84ff;
      margin-left: 7px;
      cursor: pointer;
      padding: 3px;
      font-size: 14px;
      transform: translateY(0);
    }
  }
}
</style>
