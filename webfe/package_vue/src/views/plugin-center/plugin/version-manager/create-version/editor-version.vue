<template lang="html">
  <div class="biz-create-success">
    <!-- 旧版ui -->
    <div class="new-version">
      <div class="summary-box status">
        <div class="wrapper default-box">
          <template v-if="curVersion.current_release">
            <div class="fl mr25">{{ $t('当前版本：') }} {{ curVersion.current_release.version || '--' }}</div>
            <div class="fl mr25">
              {{ $t('代码分支：') }} {{ curVersion.current_release.source_version_name || '--' }}
            </div>
            <div class="fl mr25">{{ $t('CommitID：') }} {{ curVersion.current_release.source_hash || '--' }}</div>
            <div class="fl">
              {{ $t('由') }} {{ curVersion.current_release.creator || '--' }} {{ $t(' 于 ') }}
              {{ curVersion.current_release.created }} {{ $t('发布') }}
            </div>
          </template>
          <div class="fl mr25" v-else>{{ $t('暂无已发布成功的版本') }}</div>
        </div>
      </div>

      <!-- 表单 -->
      <div class="form-box">
        <bk-form
          ref="versionForm"
          class="create-version-form-cls"
          :label-width="120"
          :model="curVersion"
          :rules="rules"
        >
          <bk-form-item
            :label="$t('代码仓库')"
            class="code-warehouse"
          >
            <bk-input
              v-model="curVersion.repository"
              :placeholder="$t('仓库地址')"
              readonly
            />
            <div class="icon-wrapper">
              <a
                :href="curVersion.repository"
                target="_blank"
                style="color: #979ba5"
              >
                <i class="paasng-icon paasng-jump-link icon-cls-link mr5" />
              </a>
              <i
                v-copy="curVersion.repository"
                class="paasng-icon paasng-general-copy icon-cls-copy"
              />
            </div>
          </bk-form-item>
          <bk-form-item
            :label="curVersionData.version_type === 'tag' ? $t('代码 Tag') : $t('代码分支')"
            :required="true"
            :icon-offset="118"
            :property="'source_versions'"
          >
            <div class="source-versions-wrapper">
              <bk-select
                v-model="curVersion.source_versions"
                :disabled="false"
                ext-cls="select-custom-cls"
                :placeholder="codeBranchPlaceholder"
                searchable
                :loading="loading"
                @change="handleSourceVersionChange"
              >
                <!-- curVersionData.allow_duplicate_source_version为false，不能选择released_source_versions中的值 -->
                <bk-option
                  v-for="option in sourceVersions"
                  :id="option.name"
                  :key="option.name"
                  :name="option.name"
                  :disabled="isOptionDisabled(option)"
                  v-bk-tooltips="{
                    content: $t('当前分支正在测试中，请先终止测试才能新建版本'),
                    disabled: isOfficialVersion || !isOptionDisabled(option)
                  }"
                />
                <div
                  v-if="curVersionData.version_type === 'tag'"
                  slot="extension"
                  style="cursor: pointer;text-align: center"
                  @click="handleAddTag"
                >
                  <i class="bk-icon icon-plus-circle mr5" />
                  {{ $t('新建 Tag') }}
                </div>
              </bk-select>
              <span v-bk-tooltips="{ content: $t('暂无可对比的代码版本'), disabled: curVersion.current_release }">
                <bk-button
                  class="code-differences"
                  :theme="'default'"
                  type="submit"
                  :disabled="!curVersion.current_release"
                  @click="handleShowCommits">
                  <i class="paasng-icon paasng-diff-4"></i>
                  {{ $t('代码差异') }}
                </bk-button>
              </span>
            </div>
            <div
              class="ribbon"
              :style="{ 'right': -offset + 'px' }"
            >
              <bk-button :text="true" :title="$t('刷新')" class="mr15" @click="refresh">
                {{ $t('刷新') }}
              </bk-button>
            </div>
          </bk-form-item>
          <bk-form-item
            v-if="curVersion.version_no === 'automatic'"
            :label="$t('版本类型')"
            :required="true"
            :property="'version'"
            :error-display-type="'normal'"
          >
            <bk-radio-group
              v-model="curVersion.version"
              @change="changeVersionType"
            >
              <!-- 示例 -->
              <bk-radio
                v-bk-tooltips.top="$t('非兼容式升级时使用')"
                :value="curVersion.semver_choices.major"
              >
                <span v-dashed="12">{{ $t('重大版本') }}</span>
              </bk-radio>
              <bk-radio
                v-bk-tooltips.top="$t('兼容式功能更新时使用')"
                :value="curVersion.semver_choices.minor"
              >
                <span v-dashed="12">{{ $t('次版本') }}</span>
              </bk-radio>
              <bk-radio
                v-bk-tooltips.top="$t('兼容式问题修正时使用')"
                :value="curVersion.semver_choices.patch"
              >
                <span v-dashed="12">{{ $t('修正版本') }}</span>
              </bk-radio>
            </bk-radio-group>
          </bk-form-item>
          <bk-form-item
            :label="isOfficialVersion ? $t('版本号') : $t('测试号')"
            :required="true"
            :property="'version'"
          >
            <bk-input
              v-model="curVersion.version"
              :placeholder="isOfficialVersion ? $t('版本号') : $t('测试号')"
              :disabled="curVersion.version_no !== 'self-fill'"
            />
          </bk-form-item>
          <bk-form-item label="CommitID">
            {{ commitId }}
          </bk-form-item>
          <bk-form-item
            :label="$t('版本日志-label')"
            :required="true"
            :property="'comment'"
          >
            <bk-input
              v-model="curVersion.comment"
              :rows="5"
              type="textarea"
              :spellcheck="false"
            />
          </bk-form-item>
          <bk-form-item label="">
            <div
              v-bk-tooltips.top="{ content: $t('已有发布任务进行中'), disabled: !isReleaseDisabled }"
              style="display: inline-block"
            >
              <!-- 测试无需限制 -->
              <bk-button
                theme="primary"
                :loading="isSubmitLoading"
                :disabled="isReleaseDisabled"
                @click="submitVersionForm"
              >
                {{ isOfficialVersion ? $t('提交并发布') : $t('提交并开始测试') }}
              </bk-button>
            </div>
          </bk-form-item>
        </bk-form>
      </div>
    </div>

    <!-- 详情 -->
    <bk-sideslider
      :is-show.sync="versionDetail.isShow"
      :quick-close="true"
      :width="960"
    >
      <div slot="header">
        {{ $t('测试详情') }}
      </div>
      <div
        slot="content"
        class="p20"
      >
        <bk-table
          v-bkloading="{ isLoading: isLogLoading }"
          class="ps-version-list"
          :data="versionList"
          :outer-border="false"
          :size="'small'"
          :pagination="pagination"
        >
          <div slot="empty">
            <table-empty empty />
          </div>
          <bk-table-column
            :label="$t('Commit ID')"
            prop="name"
            :show-overflow-tooltip="true"
            :render-header="$renderHeader"
          />
          <bk-table-column
            :label="$t('状态')"
            prop="environment_name"
          >
            <template slot-scope="props">
              <span v-if="props.row.environment_name === 'stag'">{{ $t('已测试') }}</span>
              <span v-else>{{ $t('未测试') }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('提交者')"
            prop="operator"
            :render-header="$renderHeader"
          />
          <bk-table-column
            :label="$t('提交时间')"
            :render-header="$renderHeader"
          >
            <template slot-scope="{ row }">
              <span v-bk-tooltips="row.message">{{ row.message || '--' }}</span>
            </template>
          </bk-table-column>
          <bk-table-column label="log">
            <template slot-scope="{ row }">
              <span v-bk-tooltips="row.message">{{ row.message || '--' }}</span>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import { formatTime } from '@/common/tools';
import dayjs from 'dayjs';

export default {
  mixins: [pluginBaseMixin],
  props: {
    scheme: {
      type: Object,
      default: () => {},
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      versionDetail: {
        isShow: false,
      },
      versionList: [],
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      curVersion: {
        // 仓库地址
        repository: '',
        // 代码分支
        source_versions: '',
        // 版本类型
        semver_choices: {},
        // 版本号
        version: '',
        // 版本日志
        comment: '',
      },
      sourceVersions: [],
      isLogLoading: false,
      isSubmitLoading: false,
      curVersionData: {
        source_versions: [],
      },
      formatTime,
      offset: 138,
      rules: {
        source_versions: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
        ],
        version: [
          {
            required: true,
            message: this.$t('请选择版本类型'),
            trigger: 'blur',
          },
        ],
        comment: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    isPending() {
      return this.$route.query.isPending;
    },
    curPluginInfo() {
      return this.$store.state.plugin.curPluginInfo;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    versionType() {
      return this.$route.query.type || 'prod';
    },
    isOfficialVersion() {
      return this.versionType === 'prod';
    },
    isReleaseDisabled() {
      return this.isOfficialVersion ? this.isPending : false;
    },
    codeBranchPlaceholder() {
      const revisionPolicy = this.curVersionData.revision_policy;
      return revisionPolicy === 'disallow_releasing_source_version' ? this.$t('请选择代码分支，正在发布的代码分支不可选择') : this.$t('请选择版本，已经发布过的版本不可选择');
    },
    commitId() {
      return this.sourceVersions.find(item => item.name === this.curVersion.source_versions)?.revision || '--';
    },
  },
  watch: {
    'curVersion.source_versions'() {
      const versionData = this.sourceVersions.find(item => item.name === this.curVersion.source_versions) || {};
      this.curVersion.comment = versionData.message;
      if (this.curVersion.version_no === 'revision' || this.curVersion.version_no === 'commit-hash') {
        if (this.curVersion.version_no === 'revision') {
          this.curVersion.version = versionData.name;
        } else {
          this.curVersion.version = versionData.revision;
        }
      }
    },
    loading(newVal) {
      if (!newVal) {
        this.$nextTick(() => {
          this.offset = document.querySelector('.ribbon')?.offsetWidth + 10 || 138;
        });
      }
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.formatScheme(this.scheme);
      this.curVersion.repository = this.curPluginInfo.repository;
    },

    // 处理 scheme
    formatScheme(res) {
      this.curVersionData = res;
      this.curVersion.doc = res.doc;
      this.sourceVersions = res.source_versions;
      this.curVersion.current_release = res.current_release;
      // version_no 版本号生成规则, 自动生成(automatic),与代码版本一致(revision),与提交哈希一致(commit-hash),用户自助填写(self-fill)
      this.curVersion.semver_choices = res.semver_choices;
      const firstSourceVersion = res.source_versions[0] || {};
      // source_versions 会存在 [] 情况
      if (res.revision_policy === null) {
        this.curVersion.source_versions = firstSourceVersion?.name || '';
        this.curVersion.comment = firstSourceVersion?.message || '';
      } else {
        this.curVersion.source_versions = '';
      }
      // 版本号映射
      const versionMapping = {
        revision: firstSourceVersion.name || '', // 与代码版本一致(revision)
        'commit-hash': firstSourceVersion.revision || '', // 提交哈希一致(commit-hash)
        automatic: '', // 自动生成(automatic), 版本类型用户自行选择
        'self-fill': '', // 用户自助填写(self-fill)
      };
      this.curVersion.version = versionMapping[res.version_no] || '';
      this.curVersion.version_no = res.version_no;
    },
    refresh() {
      this.$emit('refresh');
    },

    submitVersionForm() {
      this.$refs.versionForm.validate().then(() => {
        this.createVersion();
      }, (validator) => {
        console.error(validator.content);
      });
    },

    // 新建版本并发布
    async createVersion() {
      this.isSubmitLoading = true;
      // 当前选中分支的数据
      const versionData = this.sourceVersions.filter(item => item.name === this.curVersion.source_versions);

      // 数据
      const data = {
        source_version_type: versionData[0].type,
        source_version_name: versionData[0].name,
        version: this.curVersion.version,
        comment: this.curVersion.comment,
        type: this.versionType,
      };

      // 仅 versionNo=automatic 需要传递
      if (this.curVersion.version_no === 'automatic') {
        for (const key in this.curVersion.semver_choices) {
          if (this.curVersion.semver_choices[key] === this.curVersion.version) {
            data.semver_type = key;
          }
        }
      }

      const params = {
        pdId: this.pdId,
        pluginId: this.pluginId,
        data,
      };

      try {
        const res = await this.$store.dispatch('plugin/createVersion', params);
        this.$bkMessage({
          theme: 'success',
          message: this.$t('新建成功!'),
        });
        // 跳转至发布详情
        this.goRelease(res);
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isSubmitLoading = false;
      }
    },

    goBack() {
      this.$router.push({
        name: 'pluginVersionManager',
      });
    },

    goRelease(data) {
      this.$router.push({
        name: 'pluginVersionRelease',
        query: {
          release_id: data.id,
          type: this.versionType,
        },
      });
    },

    async handleShowCommits() {
      if (!this.curVersion.source_versions) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('请选择代码分支'),
        });
        return false;
      }

      const fromRevision = this.curVersion.current_release.source_hash;
      const curCodeItem = this.sourceVersions.filter(item => item.name === this.curVersion.source_versions);
      const toRevision = `${curCodeItem[0].type}:${curCodeItem[0].name}`;
      const res = await this.$store.dispatch('plugin/getGitCompareUrl', {
        pdId: this.pdId,
        pluginId: this.pluginId,
        fromRevision,
        toRevision,
      });
      window.open(res.result, '_blank');
    },

    handlerCancel() {
      this.isSubmitLoading = false;
    },

    changeVersionType() {
      this.$refs.versionForm.validate().catch((e) => {
        console.error(e);
      });
    },

    // 新建Tag
    handleAddTag() {
      const url = this.curVersion.repository.replace('.git', '/-/tags/new');
      window.open(url, '_blank');
    },

    // 当前代码分支是否可以选择
    isOptionDisabled(data) {
      const revisionPolicy = this.curVersionData.revision_policy;
      if (revisionPolicy === null) {
        return false;
      }
      // 不允许选择已经发布过的代码分支
      if (revisionPolicy === 'disallow_released_source_version') {
        return this.curVersionData.released_source_versions.includes(data.name);
      }
      // 不允许选择正在发布的代码分支
      if (revisionPolicy === 'disallow_releasing_source_version') {
        return this.curVersionData.releasing_source_versions.includes(data.name);
      }
      return false;
    },

    handleSourceVersionChange(v) {
      if (this.curVersionData.version_no === 'branch-timestamp') {
        const time = dayjs().format('YYMMDDHHmm');
        this.curVersion.version = `${v}-${time}`;
        const curVersionData = this.sourceVersions.find(item => item.name === v) || {};
        this.curVersion.comment = curVersionData.message;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.new-version {
  padding: 24px;
  background: #fff;
  box-shadow: 0 2px 4px 0 #1919290d;
  border-radius: 2px;
}
.app-container {
  padding: 0;
}
.header-title {
  display: flex;
  align-items: center;
  .app-code {
    color: #979ba5;
  }
  .arrows {
    margin: 0 9px;
    transform: rotate(-90deg);
    font-size: 12px;
    font-weight: 600;
    color: #979ba5;
  }
}

.detail-wrapper {
  .item-info {
    display: flex;
    height: 40px;
    line-height: 40px;
    border-top: 1px solid #dfe0e5;

    &:last-child {
      border-bottom: 1px solid #dfe0e5;
    }

    .describe,
    .content {
      display: flex;
      align-items: center;
    }

    .describe {
      flex-direction: row-reverse;
      width: 100px;
      text-align: right;
      padding-right: 16px;
      font-size: 12px;
      color: #979ba5;
      background: #fafbfd;
    }
    .content {
      flex: 1;
      font-size: 12px;
      color: #63656e;
      padding: 10px 0 10px 16px;
      border-left: 1px solid #f0f1f5;
    }
  }

  .h-auto {
    height: auto;
    line-height: 22px;
  }
}

.source-versions-wrapper {
  display: flex;
  .bk-select {
    flex: 1;
  }
  .code-differences {
    margin-left: 8px;
    .paasng-diff-4 {
      color: #979BA5;
    }
  }
}

:deep(.create-version-form-cls) {
  .bk-label {
    font-size: 12px;
  }
}

.detail-doc {
  color: #3a84ff;
  cursor: pointer;
}

.form-box {
  width: 650px;

  & /deep/ .bk-form-control .group-box {
    border-left: none;
    border-color: #3a84ff !important;
  }

  .icon-wrapper {
    display: flex;
    align-items: center;
    position: absolute;
    right: 0px;
    top: 0px;
    height: 100%;
    font-size: 16px;
    padding-right: 6px;
    color: #979ba5;

    a,
    .icon-cls-copy {
      transform: translateY(0px);
    }

    .icon-cls-link:hover,
    .icon-cls-copy:hover {
      cursor: pointer;
      color: #3a84ff;
    }
  }

  .ribbon {
    display: flex;
    position: absolute;
    right: -138px;
    top: 0px;
    color: #3a84ff;

    &.en-cls {
      right: -158px;
    }

    &:hover {
      color: #699df4;
    }

    div {
      cursor: pointer;
    }
  }

  .environment-wrapper {
    margin-top: 5px;
    padding: 5px 0;
    background: #f5f7fa;
    border-radius: 2px;
    padding-left: 28px;
  }
}

.icon-cls-return {
  font-weight: 700;
  font-size: 16px;
  cursor: pointer;
  color: #3a84ff;
}

.summary-box {
  padding-bottom: 20px;
  background: #fff;
  font-size: 12px;

  .wrapper {
    height: 64px;
    background: #f5f6fa;
    border-radius: 2px;
    line-height: 64px;
    padding: 0 20px;

    &::after {
      display: block;
      clear: both;
      content: '';
      font-size: 0;
      height: 0;
      visibility: hidden;
    }

    &.default-box {
      padding: 11px 12px 11px 20px;
      height: auto;
      line-height: 16px;
      color: #979ba5;
      .span {
        height: 16px;
      }
    }

    &.not-deploy {
      height: 42px;
      line-height: 42px;
    }

    &.primary {
      background: #e1ecff;
      color: #979ba5;
    }

    &.warning {
      background: #fff4e2;
      border-color: #ffdfac;

      .paasng-icon {
        color: #fe9f07;
      }
    }

    &.danger {
      background: #ffecec;
      color: #979ba5;

      .paasng-icon {
        color: #eb3635;
        position: relative;
        top: 4px;
        font-size: 32px;
      }
    }

    &.success {
      background: #e7fcfa;
      color: #979ba5;

      .paasng-icon {
        position: relative;
        top: 4px;
        color: #3fc06d;
        font-size: 32px;
      }
    }
  }
}

.line {
  position: relative;
  margin: 26px 0;
  max-width: 1080px;
  min-width: 1080px;
  border-top: 1px solid #f0f1f5;
}
.version-info-wrapper div {
  font-size: 14px;
  color: #63656e;
  line-height: 32px;
  word-break: break-all;
}

.code-branch-tip {
  font-size: 12px;
  color: #979ba5;
}

.select-custom-cls {
  background: #fff;
}
</style>

<style lang="css">
.form-box .code-warehouse .bk-form-input {
  padding-right: 50px !important;
}
.form-box .cls-test-env .bk-form-content .bk-form-control > .bk-form-radio:first-child {
  width: 82px;
}
</style>
