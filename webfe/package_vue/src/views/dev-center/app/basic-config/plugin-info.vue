<template>
  <div class="info-card-style mt16">
    <div class="title">
      {{ $t('插件信息') }}
      <div
        v-if="!pluginInfoConfig.isEdit"
        class="edit-container"
        @click="handleEdit"
      >
        <i class="paasng-icon paasng-edit-2 pl10" />
        {{ $t('编辑') }}
      </div>
    </div>
    <div class="info">
      {{ $t('管理插件相关信息') }}
    </div>
    <!-- 查看态 -->
    <section
      class="view-mode"
      v-if="!pluginInfoConfig.isEdit"
    >
      <ul class="info-warpper">
        <li class="item">
          <div class="label">{{ $t('插件简介') }}：</div>
          <div
            class="value"
            v-bk-overflow-tips
          >
            {{ curPluginData.introduction || '--' }}
          </div>
        </li>
        <li class="item">
          <div class="label">{{ $t('联系人员') }}：</div>
          <div class="value" v-bk-overflow-tips="{ content: curPluginData.contact?.join() }">
            <user
              v-if="curPluginData.contact.length"
              ref="member_selector"
              v-model="curPluginData.contact"
              :disabled="true"
              placeholder=""
              class="disabled-plugin-member-cls"
            />
            <span v-else>--</span>
            <!-- {{ curPluginData.contact.join() || '--' }} -->
          </div>
        </li>
        <li class="item">
          <div class="label">{{ $t('蓝鲸网关') }}：</div>
          <div
            class="value api-gw"
            v-bk-overflow-tips
          >
            <span
              v-if="apiGwName"
              style="color: #3a84ff"
            >
              {{ $t('已绑定到') + apiGwName }}
            </span>
            <span
              v-else
              style="color: #979ba5"
            >
              {{ $t('暂未找到已同步网关') }}
            </span>
            <i
              v-bk-tooltips="$t('网关维护者默认为应用管理员')"
              class="bk-icon icon-info"
            />
          </div>
        </li>
        <li class="item">
          <div class="label">{{ $t('插件分类') }}：</div>
          <div
            class="value"
            v-bk-overflow-tips
          >
            {{ currentPluginCategory }}
          </div>
        </li>
        <li class="item">
          <div class="label">{{ $t('插件使用方') }}：</div>
          <div
            class="value"
            v-bk-overflow-tips
          >
            {{ pluginUsers.length ? pluginUsers.join(',') : '--' }}
          </div>
        </li>
      </ul>
    </section>
    <!-- 编辑态 -->
    <section
      class="edit-mode"
      v-else
    >
      <bk-form
        :label-width="200"
        form-type="vertical"
      >
        <bk-form-item :label="$t('插件简介')">
          <bk-input v-model="pluginformData.introduction"></bk-input>
        </bk-form-item>
        <bk-form-item :label="$t('联系人员')">
          <user
            ref="member_selector"
            v-model="pluginformData.contact"
            :placeholder="$t('请输入并按Enter结束')"
          />
        </bk-form-item>
        <bk-form-item :label="$t('蓝鲸网关')">
          <div class="diabled-input-gw value api-gw">
            <span
              v-if="apiGwName"
              style="color: #3a84ff"
              v-bk-overflow-tips
            >
              {{ $t('已绑定到') + apiGwName }}
            </span>
            <span
              v-else
              style="color: #979ba5"
            >
              {{ $t('暂未找到已同步网关') }}
            </span>
            <i
              v-bk-tooltips="$t('网关维护者默认为应用管理员')"
              class="bk-icon icon-info"
            />
          </div>
        </bk-form-item>
        <bk-form-item :label="$t('插件分类')">
          <bk-select
            v-model="pluginformData.tag"
            clearable
            ext-cls="select-custom"
            searchable
          >
            <bk-option
              v-for="option in pluginTypeList"
              :id="option.id"
              :key="option.id"
              :name="option.name"
            />
          </bk-select>
        </bk-form-item>
        <!-- tips -->
        <bk-form-item :label="$t('插件使用方')">
          <bk-select
            searchable
            multiple
            display-tag
            v-model="pluginformData.distributors"
          >
            <bk-option
              v-for="option in pluginDistributors"
              :key="option.code_name"
              :id="option.code_name"
              :name="option.name"
            ></bk-option>
          </bk-select>
          <p class="plugin-users-tip">
            <i class="bk-icon icon-info" />
            {{
              $t(
                '只有授权给了某个使用方，后者才能拉取到本地插件的相关信息，并在产品中通过访问插件注册到蓝鲸网关的API来使用插件功能。除了创建时注明的“插件使用方”之外，插件默认不授权给任何其他使用方。'
              )
            }}
          </p>
        </bk-form-item>
        <bk-form-item class="mt20">
          <bk-button
            theme="primary"
            ext-cls="mr8"
            :loading="pluginInfoConfig.isLoading"
            @click.stop.prevent="updatePluginBseInfo"
          >
            {{ $t('提交') }}
          </bk-button>
          <bk-button
            theme="default"
            @click.stop="handleCancel"
          >
            {{ $t('取消') }}
          </bk-button>
        </bk-form-item>
      </bk-form>
    </section>
  </div>
</template>

<script>
import User from '@/components/user';
import { cloneDeep } from 'lodash';
export default {
  name: 'AppPluginInfo',
  components: {
    User,
  },
  data() {
    return {
      pluginInfoConfig: {
        isEdit: false,
        isLoading: false,
      },
      curPluginData: {
        contact: [],
      },
      pluginformData: {
        introduction: '',
        contact: [],
        // 插件分类
        tag: 0,
        // 插件使用方
        distributors: [],
      },
      apiGwName: '',
      pluginTypeList: [],
      pluginDistributors: [],
      pluginUsers: [],
      tipsInfo: this.$t('如果你将插件授权给某个使用方，对方便能读取到你的插件的基本信息、（通过 API 网关）调用插件的 API、并将插件能力集成到自己的系统中。'),
    };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
    currentPluginCategory() {
      return this.pluginTypeList.find(v => this.curPluginData?.tag === v.id)?.name || '--';
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.getPluginBaseInfoData();
      this.getAuthorizedPlugins();
      this.getPluginCategoryList();
      this.getPluginDistributors();
    },
    // 编辑插件信息
    handleEdit() {
      this.pluginInfoConfig.isEdit = true;
      this.pluginformData.introduction = this.curPluginData.introduction;
      this.pluginformData.contact = this.curPluginData.contact;
      this.pluginformData.tag = this.curPluginData.tag;
      this.pluginformData.distributors = this.pluginUsers;
    },
    // 取消
    handleCancel() {
      this.pluginInfoConfig.isEdit = false;
    },
    // 获取插件基础信息
    async getPluginBaseInfoData() {
      try {
        const res = await this.$store.dispatch('plugin/getPluginBaseInfoData', {
          appCode: this.appCode,
        });
        res.contact = res.contact.length ? res.contact.split(',') : [];
        this.apiGwName = res.api_gw_name;
        this.curPluginData = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    // 获取插件分类列表
    async getPluginCategoryList() {
      try {
        const data = await this.$store.dispatch('market/getPluginTypeList');
        this.pluginTypeList = data || [];
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    // 获取已授权插件
    async getAuthorizedPlugins() {
      try {
        const res = await this.$store.dispatch('plugin/getAuthorizedPlugins', {
          appCode: this.appCode,
        });
        this.pluginUsers = res.map(item => item.code_name);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    // 获取插件使用方列表
    async getPluginDistributors() {
      try {
        const data = await this.$store.dispatch('plugin/getPluginDistributors', {
          appCode: this.appCode,
        });
        this.pluginDistributors = data || [];
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    // 更新插件基本信息&插件使用方信息
    async updatePluginBseInfo() {
      this.pluginInfoConfig.isLoading = true;
      const data = cloneDeep(this.pluginformData);
      data.contact = data.contact.join();
      if (!data.distributors.length) {
        delete data.distributors;
      }

      try {
        await this.$store.dispatch('plugin/updatePluginBseInfo', {
          appCode: this.appCode,
          data,
        });
        await Promise.all([this.getPluginBaseInfoData(), this.getAuthorizedPlugins()]);
        this.$paasMessage({
          theme: 'success',
          message: this.$t('插件信息修改成功！'),
        });
        this.handleCancel();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.pluginInfoConfig.isLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.title {
  display: flex;
  align-items: flex-end;
  font-weight: 700;
  font-size: 14px;
  color: #313238;
  margin-bottom: 4px;

  .edit-container {
    font-size: 12px;
    color: #3a84ff;
    cursor: pointer;
  }
}
.info {
  font-size: 12px;
  color: #979ba5;
}

.view-mode {
  margin-top: 16px;
  .info-warpper {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
  .item {
    display: flex;
    align-items: center;
    min-height: 40px;
    font-size: 14px;
    color: #63656e;
    overflow: hidden;
    .label {
      width: 130px;
      text-align: right;
      flex-shrink: 0;
    }
    .value {
      width: 100%;
      color: #313238;
      text-wrap: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;

      &.api-gw i {
        color: #63656e;
      }
    }
  }
}
.edit-mode {
  margin-top: 16px;
}
.plugin-users-tip {
  i {
    font-size: 14px;
    color: #979ba5;
  }
  font-size: 12px;
  color: #979ba5;
  line-height: 20px;
  margin-top: 8px;
}
.diabled-input-gw {
  height: 32px;
  line-height: 32px;
  font-size: 12px;
  border: 1px solid #dcdee5;
  padding: 0 10px;
  border-radius: 2px;
  background: #fafbfd;
  cursor: not-allowed;
}
</style>

<style lang="scss">
.disabled-plugin-member-cls {
  .bk-tag-selector .bk-tag-input.disabled {
    border: none !important;
    background: #fff;
  }

  .bk-rtx-member-selector img.bk-member-loading {
    display: none;
  }
}
</style>
