<template>
  <div class="new-code-repository-form">
    <div class="readonly-text repository-url">
      <span
        class="text-ellipsis"
        v-bk-overflow-tips
      >
        {{ formData.repository_url || '--' }}
      </span>
    </div>
    <bk-select
      ext-cls="flex-1 f14"
      v-model="selectValue"
      :clearable="false"
      :loading="selectLoading"
    >
      <bk-option
        v-for="option in selectOptions"
        :key="option.name"
        :id="option.name"
        :name="option.path"
      ></bk-option>
    </bk-select>
    <div class="readonly-text split">/</div>
    <!-- 仓库名：appId-moduleName -->
    <bk-input
      v-model="repositoryName"
      ext-cls="flex-1 repository-name"
    ></bk-input>
    <div class="readonly-text suffix">.git</div>
  </div>
</template>

<script>
import { mapState } from 'vuex';

export default {
  name: 'NewCodeRepositoryForm',
  props: {
    appId: {
      type: String,
      required: true,
      default: '',
    },
    moduleName: {
      type: String,
      default: 'default',
    },
    list: {
      type: Array,
      default: () => [],
    },
    data: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      formData: {
        repository_url: '',
      },
      repositoryName: '',
      selectValue: '',
      selectLoading: false,
      selectOptions: [],
    };
  },
  computed: {
    ...mapState(['curUserInfo']),
    curUsername() {
      return this.curUserInfo.username || '';
    },
  },
  watch: {
    list: {
      handler(newList) {
        if (newList.length) {
          const firstItem = newList[0];
          this.formData = firstItem;
          this.getNewCodeRepositoryOptions(firstItem.value);
        }
      },
      deep: true,
      immediate: true,
    },
    appId: {
      handler(newAppId) {
        this.repositoryName = this.formatRepositoryName(newAppId, this.moduleName);
      },
      immediate: true,
    },
    moduleName: {
      handler(newModuleName) {
        this.repositoryName = this.formatRepositoryName(this.appId, newModuleName);
      },
      immediate: true,
    },
  },
  methods: {
    async getNewCodeRepositoryOptions(type) {
      this.selectLoading = true;
      try {
        const res = await this.$store.dispatch('createApp/getNewCodeRepositoryOptions', { type });
        // 将当前用户名作为默认选项
        const baseOption = { name: this.curUsername, path: this.curUsername };
        this.selectOptions = [baseOption, ...res.results] || [];
        this.selectValue = this.curUsername || '';
        if (Object.keys(this.data)?.length) {
          const curOption = this.selectOptions.find((item) => item.web_url === this.data.repo_group);
          this.selectValue = curOption?.name ?? this.curUsername;
        }
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.selectLoading = false;
      }
    },
    getFromData() {
      if (this.selectValue === this.curUsername) {
        return {
          repo_name: this.repositoryName,
        };
      }
      const selectedItem = this.selectOptions.find((item) => item.name === this.selectValue);
      return {
        repo_name: this.repositoryName,
        repo_group: selectedItem.web_url,
      };
    },
    formatRepositoryName(appId, moduleName) {
      if (moduleName) {
        return `${appId}-${moduleName}`;
      }
      return appId || '';
    },
  },
};
</script>

<style lang="scss" scoped>
.new-code-repository-form {
  width: 650px;
  display: flex;
  align-items: center;
  .readonly-text {
    display: flex;
    align-items: center;
    height: 32px;
    padding: 0 10px;
    background: #fafbfd;
    border: 1px solid #dcdee5;
    border-radius: 2px;
    font-size: 14px;
  }
  .repository-url {
    width: 150px;
  }
  .split {
    width: 30px;
  }
  .repository-name {
    /deep/ input {
      font-size: 14px;
    }
  }
  .suffix {
    width: 50px;
  }
}
</style>
