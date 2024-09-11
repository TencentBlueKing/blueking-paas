<template>
  <div class="release-content-container">
    <card
      :title="$t('发布内容')"
      :is-collapse="true"
    >
      <!-- 编辑模式 -->
      <bk-form
        v-if="isEdit"
        :model="releaseContent"
        :rules="rules"
        :label-width="120"
        ref="releaseContentForm"
        ext-cls="gray-range-form-cls"
      >
        <bk-form-item
          :label="$t('已测试版本')"
          :required="true"
          :property="'id'"
          :error-display-type="'normal'"
        >
          <bk-select
            :disabled="false"
            v-model="releaseContent.source_versions"
            searchable>
            <bk-option
              v-for="option in sourceVersions"
              :key="option.name"
              :id="option.name"
              :name="option.name">
            </bk-option>
          </bk-select>
          <p slot="tip" class="tips">
            <bk-button
              :text="true"
              title="primary"
              size="small"
              @click="toTestDetails"
            >
              <i class="paasng-icon paasng-jump-link icon-cls-link" />
              {{ $t('查看测试数据') }}
            </bk-button>
          </p>
        </bk-form-item>
        <bk-form-item
          :label="$t('版本类型')"
          :required="true"
          :property="'version'"
          :error-display-type="'normal'"
        >
          <bk-radio-group
            v-model="releaseContent.version"
            @change="changeVersionType"
          >
            <bk-radio
              v-for="item in versionTypes"
              v-bk-tooltips.top="item.tips"
              :value="item.value"
              :key="item.key"
            >
              <span v-dashed="12">{{ item.name }}</span>
            </bk-radio>
          </bk-radio-group>
        </bk-form-item>
        <!-- 回显 -->
        <bk-form-item
          :label="$t('版本号')"
          :required="true"
          :property="'version'"
          :error-display-type="'normal'"
        >
          <bk-input v-model="releaseContent.versionDisplay" :disabled="true"></bk-input>
        </bk-form-item>
        <bk-form-item
          :label="$t('版本日志')"
          :required="true"
          :property="'comment'"
          :error-display-type="'normal'"
        >
          <bk-input
            v-model="releaseContent.comment"
            :type="'textarea'"
          ></bk-input>
        </bk-form-item>
      </bk-form>

      <!-- 查看模式 -->
      <section
        class="view-mode"
        v-else
      >
        <view-mode>
          <ul>
            <li class="item">
              <div class="label">{{ $t('已测试版本') }}：</div>
              <div class="value">
                <p>{{ data.source_version_name }}</p>
                <p>
                  <bk-button
                    :text="true"
                    title="primary"
                    @click="toTestDetails"
                  >
                    <i class="paasng-icon paasng-jump-link icon-cls-link mr5" />
                    <span class="f12">{{ $t('查看测试数据') }}</span>
                  </bk-button>
                </p>
              </div>
            </li>
            <li class="item">
              <div class="label">{{ $t('版本类型') }}：</div>
              <div class="value">{{ versionTypes.find(v => v.key === data.semver_type)?.name }}</div>
            </li>
            <li class="item">
              <div class="label">{{ $t('版本号') }}：</div>
              <div class="value">{{ data.version }}</div>
            </li>
            <li class="item">
              <div class="label">{{ $t('版本日志') }}：</div>
              <div class="value">{{ data.comment }}</div>
            </li>
          </ul>
        </view-mode>
      </section>
    </card>
  </div>
</template>

<script>
import card from '@/components/card/card.vue';
import viewMode from './view-mode.vue';
import pluginBaseMixin from '@/mixins/plugin-base-mixin';

export default {
  name: 'ReleaseContent',
  components: {
    card,
    viewMode,
  },
  mixins: [pluginBaseMixin],
  props: {
    mode: {
      type: String,
      default: 'edit',
    },
    scheme: {
      type: Object,
      default: () => {},
    },
    data: {
      type: Object,
      default: () => {},
    },
    versionData: {
      type: Object,
      default: () => {},
    },
    versionInfo: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      // 发布内容
      releaseContent: {
        type: 'prod',
        // 代码分支
        source_versions: '',
        // 版本类型
        semver_type: '',
        // 版本号
        version: '',
        comment: '',
        versionDisplay: '',
      },
      sourceVersions: [],
      versionTypes: [
        { name: this.$t('重大版本'), key: 'major', value: '1.0.0', tips: this.$t('非兼容式升级时使用') },
        { name: this.$t('次版本'), key: 'minor', value: '0.1.0', tips: this.$t('兼容式功能更新时使用') },
        { name: this.$t('修正版本'), key: 'patch', value: '0.0.1', tips: this.$t('兼容式问题修正时使用') },
      ],
      rules: {
        version: [
          {
            required: true,
            message: '必填项',
            trigger: 'blur',
          },
        ],
        comment: [
          {
            required: true,
            message: '必填项',
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    isEdit() {
      return this.mode === 'edit';
    },
    curVersionData() {
      return this.sourceVersions.find(item => item.name === this.releaseContent.source_versions) || {};
    },
    versionId() {
      return this.$route.query.versionId;
    },
  },
  watch: {
    scheme: {
      handler(newValue) {
        if (this.isEdit) {
          this.formatData(newValue);
        }
      },
      immediate: true,
      deep: true,
    },
    'releaseContent.version'(newVal) {
      this.releaseContent.versionDisplay = `${newVal} (主版本号、次版本号、修正版本号)`;
    },
    'releaseContent.source_versions'() {
      this.releaseContent.comment = this.curVersionData.message;
      if (this.releaseContent.version_no === 'revision' || this.releaseContent.version_no === 'commit-hash') {
        this.releaseContent.version = this.releaseContent.version_no === 'revision' ? this.curVersionData.name : this.curVersionData.revision;
      }
    },
  },
  methods: {
    // 版本类型切换
    changeVersionType(value) {
      this.releaseContent.semver_type = this.versionTypes.find(v => v.value === value).key;
      // 版本类型切换重新校验，解决依赖性错误提示问题
      this.$refs.releaseContentForm && this.$refs.releaseContentForm.validate().catch((e) => {
        console.error(e);
      });
    },
    // 数据格式化
    formatData(data) {
      this.versionTypes.forEach((v) => {
        v.value = data.semver_choices[v.key];
      });
      this.sourceVersions = data.source_versions;
      this.releaseContent.version_no = data.version_no;
      // 设置
      if (data.revision_policy === null) {
        this.releaseContent.source_versions = data.source_versions[0]?.name || '';
        this.releaseContent.comment = data.source_versions[0]?.message || '';
      } else {
        this.releaseContent.source_versions = '';
      }
      const versionMapping = {
        revision: data.source_versions[0]?.name || '',
        'commit-hash': data.source_versions[0]?.revision || '',
        automatic: '',
        'self-fill': '',
      };
      this.releaseContent.version = versionMapping[data.version_no] || '';
      // 重新申请默认值
      if (this.versionId) {
        this.setVersionDefaultValue(data);
      }
    },
    // 重新申请设置默认值
    setVersionDefaultValue() {
      const { source_version_name, semver_type, comment } = this.versionData;
      const version = this.versionTypes.find(v => v.key === semver_type).value;
      const versionDisplay = `${version} (主版本号、次版本号、修正版本号)`;
      this.releaseContent = {
        ...this.releaseContent,
        source_versions: source_version_name,
        version,
        versionDisplay,
        comment,
        semver_type,
      };
    },
    // 表单校验
    validate() {
      return this.$refs.releaseContentForm.validate();
    },
    // 向外抛出当前表单数据
    getFormData() {
      const { version, comment, semver_type } = this.releaseContent;
      const params = {
        type: 'prod',
        source_version_type: this.curVersionData.type,
        source_version_name: this.curVersionData.name,
        release_id: this.curVersionData.extra.release_id,
        version,
        comment,
        semver_type,
      };
      return params;
    },
    // 测试详情
    toTestDetails() {
      const url = this.isEdit ? this.curVersionData.url : this.versionInfo.url;
      const id = url.split('=')[1];
      const newTabUrl = `${location.origin}/plugin-center/plugin/${this.pdId}/${this.pluginId}/version-release?release_id=${id}&type=test`;
      window.open(newTabUrl, '_blank');
    },
  },
};
</script>

<style lang="scss" scoped>
.release-content-container {
  .tips {
    .bk-button-text.bk-button-small {
      padding: 0;
      i {
        font-size: 14px;
      }
    }
  }
}
</style>
