<template>
  <section>
    <div
      class="cloud-app-container"
      v-bkloading="{ isLoading: formLoading, opacity: 1 }"
    >
      <bk-alert
        class="mb20 mt20"
        :type="isAllowCreateApp ? 'info' : 'warning'"
        :title="
          isAllowCreateApp
            ? $t(
                '基于容器镜像来部署应用，支持用 YAML 格式文件描述应用模型，可使用进程管理、云 API 权限及各类增强服务等平台基础能力'
              )
            : notAllowCreateAppMessage
        "
      ></bk-alert>

      <div class="default-app-type mb20">
        <default-app-type @on-change-type="handleSwitchAppType" />
      </div>
      <!-- 不是smart应用 -->
      <section v-if="curCodeSource !== 'smart'">
        <bk-form
          ref="formBaseRef"
          :model="formData"
          :rules="rules"
          :label-width="100"
          class="from-content"
        >
          <div class="form-item-title mb10">
            {{ $t('基本信息') }}
          </div>
          <bk-form-item
            :required="true"
            :property="'code'"
            :rules="rules.code"
            error-display-type="normal"
            ext-cls="form-item-cls"
            :label="$t('应用 ID')"
          >
            <bk-input
              v-model="formData.code"
              :placeholder="
                isBkLesscode
                  ? $t('由小写字母组成，长度小于 16 个字符')
                  : $t('请输入 3-16 字符的小写字母、数字、连字符(-)，以小写字母开头')
              "
              class="form-input-width"
            ></bk-input>
            <p
              slot="tip"
              class="input-tips"
            >
              {{ $t('应用的唯一标识，创建后不可修改') }}
            </p>
          </bk-form-item>
          <bk-form-item
            :required="true"
            :property="'name'"
            :rules="rules.name"
            error-display-type="normal"
            ext-cls="form-item-cls mt20"
            :label="$t('应用名称')"
          >
            <bk-input
              v-model="formData.name"
              :placeholder="
                isBkLesscode
                  ? $t('由汉字、英文字母、数字组成，长度不超过 20 个字符')
                  : $t('由汉字、英文字母、数字、连字符（-）组成，长度不超过 20 个字符')
              "
              class="form-input-width"
            ></bk-input>
          </bk-form-item>
          <!-- 多租户 -->
          <template v-if="isShowTenant">
            <bk-form-item
              :required="true"
              :property="'tenant'"
              error-display-type="normal"
              ext-cls="form-item-cls"
              :label="$t('租户模式')"
            >
              <bk-radio-group v-model="formData.tenantMode">
                <bk-radio-button value="single">{{ $t('单租户') }}</bk-radio-button>
                <bk-radio-button value="global">{{ $t('全租户') }}</bk-radio-button>
              </bk-radio-group>
            </bk-form-item>
            <bk-form-item
              v-if="formData.tenantMode === 'single'"
              :required="true"
              ext-cls="form-item-cls"
              :label="$t('租户 ID')"
            >
              <bk-input
                class="form-input-width"
                :value="tenantId"
                :disabled="true"
              ></bk-input>
            </bk-form-item>
          </template>
          <!-- 镜像仓库不需要展示构建方式 -->
          <bk-form-item
            :required="true"
            error-display-type="normal"
            ext-cls="form-item-cls mt20"
            :label="$t('构建方式')"
            v-if="isBkDefaultCode && formData.buildMethod !== 'image'"
          >
            <div class="mt5">
              <bk-radio-group
                v-model="formData.buildMethod"
                class="construction-manner"
                @change="handleChangeBuildMethod"
              >
                <bk-radio :value="'buildpack'">
                  {{ $t('蓝鲸 Buildpack') }}
                  <span
                    class="tips"
                    @click.stop
                  >
                    <bk-icon type="info-circle" />
                    {{ $t('使用构建工具从源码仓库构建镜像，支持多种编程语言，提供开发框架，支持原普通应用所有功能') }}
                  </span>
                </bk-radio>
                <bk-radio :value="'dockerfile'">
                  Dockerfile
                  <span
                    class="tips"
                    @click.stop
                  >
                    <bk-icon type="info-circle" />
                    {{ $t('基于仓库的 Dockerfile 直接构建镜像（类似 docker build），暂不提供开发框架') }}
                  </span>
                </bk-radio>
              </bk-radio-group>
            </div>
          </bk-form-item>
        </bk-form>

        <bk-steps
          ext-cls="step-cls"
          :steps="createSteps"
          :cur-step.sync="curStep"
          v-if="isBkDefaultCode"
        ></bk-steps>

        <section v-if="formData.sourceOrigin === 'image' && curStep === 1">
          <!-- 镜像管理 -->
          <bk-form
            ref="formImageRef"
            :model="formData"
            :rules="rules"
            :label-width="100"
            class="from-content mt20"
          >
            <div class="form-item-title mb10">
              {{ $t('镜像信息') }}
            </div>
            <bk-form-item
              :required="true"
              :property="'url'"
              error-display-type="normal"
              ext-cls="form-item-cls"
              :label="$t('镜像仓库')"
            >
              <bk-input
                v-model="formData.url"
                class="form-input-width"
                clearable
                :placeholder="mirrorExamplePlaceholder"
              ></bk-input>
            </bk-form-item>
            <section class="cloud-image-credential-box flex-row">
              <div class="image-label">{{ $t('镜像凭证') }}</div>
              <bk-form-item
                error-display-type="normal"
                :property="'imageCredentialName'"
                :rules="rules.imageCredential"
              >
                <bk-input
                  class="mr10"
                  v-model="formData.imageCredentialName"
                  clearable
                  :placeholder="$t('请输入名称，如 default')"
                ></bk-input>
              </bk-form-item>
              <bk-form-item
                error-display-type="normal"
                :property="'imageCredentialUserName'"
                :rules="getImageCredentialRule('账号')"
              >
                <bk-input
                  class="mr10"
                  v-model="formData.imageCredentialUserName"
                  clearable
                  :placeholder="$t('请输入账号')"
                ></bk-input>
              </bk-form-item>
              <bk-form-item
                error-display-type="normal"
                :property="'imageCredentialPassWord'"
                :rules="getImageCredentialRule('密码')"
              >
                <bk-input
                  type="password"
                  v-model="formData.imageCredentialPassWord"
                  clearable
                  :placeholder="$t('请输入密码')"
                ></bk-input>
              </bk-form-item>
            </section>
            <p class="cloud-image-credential-tips">
              {{ $t('私有镜像需要填写镜像凭证才能拉取镜像') }}
            </p>
          </bk-form>
        </section>

        <section v-if="curStep === 1">
          <template v-if="formData.sourceOrigin === 'soundCode'">
            <!-- 代码仓库 -->
            <section v-if="isBkDefaultCode">
              <bk-form
                v-if="formData.buildMethod === 'buildpack'"
                ref="formModuleRef"
                :model="formData"
                :rules="rules"
                :label-width="100"
                class="from-content mt20"
              >
                <div class="form-item-title mb10">
                  {{ $t('应用模版') }}
                </div>
                <bk-form-item
                  error-display-type="normal"
                  ext-cls="form-item-cls"
                  :label="$t('模板来源')"
                >
                  <div class="flex-row align-items-center tab-container mb20">
                    <div
                      class="tab-item template"
                      :class="[{ active: activeIndex === 1 }]"
                      @click="handleCodeTypeChange(1)"
                    >
                      {{ $t('蓝鲸开发框架') }}
                    </div>
                    <div
                      v-if="userFeature.BK_PLUGIN_TYPED_APPLICATION"
                      class="tab-item template"
                      :class="[{ active: activeIndex === 3 }]"
                      @click="handleCodeTypeChange(3)"
                    >
                      {{ $t('蓝鲸插件') }}
                    </div>
                  </div>
                </bk-form-item>
                <section v-show="isBkDevOps">
                  <bk-form-item
                    error-display-type="normal"
                    ext-cls="form-item-cls mt10"
                  >
                    <div class="flex-row justify-content-between">
                      <div class="bk-button-group">
                        <bk-button
                          v-for="(item, key) in languagesData"
                          :key="key"
                          :class="buttonActive === key ? 'is-selected' : ''"
                          @click="handleSelected(item, key)"
                        >
                          {{ $t(defaultlangName[key]) }}
                        </bk-button>
                      </div>
                    </div>
                  </bk-form-item>
                  <div class="languages-card">
                    <bk-radio-group v-model="formData.sourceInitTemplate">
                      <div
                        v-for="item in languagesList"
                        :key="item.name"
                        class="pb20"
                      >
                        <bk-radio :value="item.name">
                          <div class="languages-name pl5">
                            {{ item.display_name }}
                          </div>
                          <div class="languages-desc pl5">
                            {{ item.description }}
                          </div>
                        </bk-radio>
                      </div>
                    </bk-radio-group>
                  </div>
                </section>
                <div
                  v-show="isBkPlugin"
                  class="plugin-container"
                >
                  <ul class="establish-main-list">
                    <bk-radio-group v-model="curPluginTemplate">
                      <li
                        class="plugin-item"
                        v-for="item in pluginTmpls"
                        :key="item.name"
                      >
                        <label class="pointer">
                          <bk-radio :value="item.name">{{ item.display_name }}</bk-radio>
                        </label>
                        <p class="f12 mt5">
                          {{ item.description }}
                        </p>
                      </li>
                    </bk-radio-group>
                  </ul>
                </div>
              </bk-form>
            </section>

            <!-- 蓝鲸运维开发平台 -->
            <section v-if="isBkLesscode">
              <bk-form
                :label-width="100"
                class="from-content mt20"
              >
                <div class="form-item-title mb10">
                  {{ $t('应用模版') }}
                </div>
                <bk-form-item
                  error-display-type="normal"
                  ext-cls="form-item-cls"
                  :label="$t('模板来源')"
                >
                  <div>{{ $t('蓝鲸运维开发平台') }}</div>
                </bk-form-item>
                <bk-alert
                  type="info"
                  class="lesscode-info"
                >
                  <div slot="title">
                    {{ $t('默认模块需要在') }}
                    <a
                      target="_blank"
                      :href="GLOBAL.LINK.LESSCODE_INDEX"
                      style="color: #3a84ff"
                    >
                      {{ $t('蓝鲸运维开发平台') }}
                    </a>
                    {{ $t('生成源码包部署，您也可以在应用中新增普通模块。') }}
                  </div>
                </bk-alert>
              </bk-form>
            </section>

            <bk-form
              v-if="isBkDefaultCode"
              ref="formSourceRef"
              :model="formData"
              :rules="rules"
              :label-width="100"
              class="from-content mt20"
            >
              <div class="form-item-title mb10">{{ $t('源码管理') }}</div>

              <template v-if="codeRepositoryConfig.creationRepositories?.length">
                <bk-form-item
                  :required="true"
                  :label="$t('仓库类型')"
                  ext-cls="form-item-cls mt20"
                >
                  <bk-radio-group v-model="codeRepositoryConfig.type">
                    <bk-radio :value="'existing'">{{ $t('已有代码仓库') }}</bk-radio>
                    <bk-radio :value="'platform'">
                      {{ $t('新建代码仓库（由平台自动创建）') }}
                    </bk-radio>
                  </bk-radio-group>
                </bk-form-item>

                <!-- 新建代码仓库（由平台自动创建） -->
                <template v-if="isCreatedByPlatform">
                  <bk-form-item
                    :required="true"
                    :label="$t('代码源')"
                    ext-cls="form-item-cls mt20"
                  >
                    <!-- 默认只有一项 -->
                    <CodeSourceSelector
                      :items="codeRepositoryConfig.creationRepositories"
                      :value="0"
                      :clickable="false"
                      :auto-select-single="true"
                      selection-type="index"
                    />
                  </bk-form-item>

                  <bk-form-item
                    v-if="gitExtendConfig[sourceControlTypeItem]?.isAuth"
                    :required="true"
                    :label="$t('代码仓库')"
                    ext-cls="form-item-cls mt20"
                  >
                    <!-- 创建应用只需展示应用 code -->
                    <PlatformCodeRepositoryForm
                      ref="newCodeRepositoryForm"
                      :app-id="formData.code"
                      :module-name="''"
                      :list="codeRepositoryConfig.creationRepositories"
                      :data="codeRepositoryConfig.formData"
                    ></PlatformCodeRepositoryForm>
                    <p
                      slot="tip"
                      class="g-tip"
                    >
                      {{ $t('将自动创建该私有仓库并完成模板代码初始化，当前用户默认为仓库管理员') }}
                    </p>
                  </bk-form-item>
                  <!-- 未授权提示 -->
                  <UnauthorizedTips
                    v-else
                    class="mt20"
                    :type="sourceControlTypeItem"
                    :data="gitExtendConfig[sourceControlTypeItem]"
                  />
                </template>
              </template>

              <template v-if="!isCreatedByPlatform">
                <bk-form-item
                  :required="true"
                  :label="$t('代码源')"
                  error-display-type="normal"
                  ext-cls="form-item-cls mt20"
                >
                  <CodeSourceSelector
                    class="mb20"
                    :items="sourceControlTypes"
                    :value="sourceControlTypeItem"
                    selection-type="value"
                    @change="changeSourceControl"
                  />
                </bk-form-item>
                <section v-if="curSourceControl && curSourceControl.auth_method === 'oauth'">
                  <git-extend
                    ref="extend"
                    :key="sourceControlTypeItem"
                    :git-control-type="sourceControlTypeItem"
                    :is-auth="gitExtendConfig[sourceControlTypeItem].isAuth"
                    :is-loading="gitExtendConfig[sourceControlTypeItem].isLoading"
                    :alert-text="gitExtendConfig[sourceControlTypeItem].alertText"
                    :auth-address="gitExtendConfig[sourceControlTypeItem].authAddress"
                    :auth-docs="gitExtendConfig[sourceControlTypeItem].authDocs"
                    :fetch-method="gitExtendConfig[sourceControlTypeItem].fetchMethod"
                    :repo-list="gitExtendConfig[sourceControlTypeItem].repoList"
                    :selected-repo-url.sync="gitExtendConfig[sourceControlTypeItem].selectedRepoUrl"
                  />

                  <bk-form-item
                    :label="$t('构建目录')"
                    :property="'buildDir'"
                    error-display-type="normal"
                    ext-cls="form-item-cls mt20"
                  >
                    <div class="flex-row align-items-center code-depot">
                      <bk-input
                        v-model="formData.buildDir"
                        class="form-input-width"
                        :placeholder="$t('请输入应用所在子目录，不填则默认为根目录')"
                      />
                    </div>
                  </bk-form-item>
                </section>

                <section v-if="curSourceControl && curSourceControl.auth_method === 'basic'">
                  <repo-info
                    ref="repoInfo"
                    :key="sourceControlTypeItem"
                    :type="sourceControlTypeItem"
                    :source-dir-label="'构建目录'"
                    :is-cloud-created="true"
                    :default-url="repoData.url"
                    :default-account="repoData.account"
                    :default-password="repoData.password"
                    :default-dir="repoData.sourceDir"
                    @dir-change="($event) => (curRepoDir = $event)"
                  />
                </section>

                <!-- Dockerfile 构建 -->
                <bk-form-item
                  v-if="isDockerfile"
                  :label="$t('Dockerfile 路径')"
                  :rules="absolutePathRule"
                  :property="'dockerfilePath'"
                  error-display-type="normal"
                  ext-cls="form-dockerfile-cls mt20"
                >
                  <div class="flex-row align-items-center code-depot">
                    <bk-input
                      v-model="formData.dockerfilePath"
                      class="form-input-width"
                      :placeholder="$t('相对于构建目录的路径，若留空，默认为构建目录下名为 “Dockerfile” 的文件')"
                    />
                  </div>
                </bk-form-item>

                <!-- 用户输入 构建目录 + Dockerfile 路径文件示例目录 -->
                <ExamplesDirectory
                  style="margin-left: 100px"
                  :root-path="rootPath"
                  :append-path="appendPath"
                  :default-files="defaultFiles"
                  :is-dockerfile="isDockerfile"
                  :show-root="false"
                  :type="'string'"
                />

                <!-- 构建参数 -->
                <template v-if="isDockerfile">
                  <bk-form
                    :model="dockerfileData"
                    form-type="vertical"
                    ext-cls="build-params-form"
                  >
                    <div class="form-label">
                      {{ $t('构建参数') }}
                    </div>
                    <div class="form-value-wrapper">
                      <bk-button
                        v-if="!dockerfileData.buildParams.length"
                        :text="true"
                        title="primary"
                        @click="addBuildParams"
                      >
                        <i class="paasng-icon paasng-plus-thick" />
                        {{ $t('新建构建参数') }}
                      </bk-button>
                      <template v-if="dockerfileData.buildParams.length">
                        <div class="build-params-header">
                          <div class="name">{{ $t('参数名') }}</div>
                          <div class="value">{{ $t('参数值') }}</div>
                        </div>
                        <div
                          v-for="(item, index) in dockerfileData.buildParams"
                          class="build-params-item"
                          :key="index"
                        >
                          <bk-form
                            :ref="`name-${index}`"
                            :model="item"
                          >
                            <bk-form-item
                              :rules="rules.buildParams"
                              :property="'name'"
                            >
                              <bk-input
                                v-model="item.name"
                                :placeholder="$t('参数名')"
                              ></bk-input>
                            </bk-form-item>
                          </bk-form>
                          <span class="equal">=</span>
                          <bk-form
                            :ref="`value-${index}`"
                            :model="item"
                          >
                            <bk-form-item
                              :rules="rules.buildParams"
                              :property="'value'"
                            >
                              <bk-input v-model="item.value"></bk-input>
                            </bk-form-item>
                          </bk-form>
                          <i
                            class="paasng-icon paasng-minus-circle-shape"
                            @click="removeBuildParams(index)"
                          ></i>
                        </div>
                      </template>
                    </div>
                  </bk-form>
                  <bk-button
                    v-if="dockerfileData.buildParams.length"
                    ext-cls="add-build-params"
                    :text="true"
                    title="primary"
                    @click="addBuildParams"
                  >
                    <i class="paasng-icon paasng-plus-thick" />
                    {{ $t('新建构建参数') }}
                  </bk-button>
                </template>
              </template>
            </bk-form>
          </template>

          <bk-form
            v-if="isShowAdvancedOptions"
            :model="formData"
            :rules="rules"
            :label-width="100"
            class="from-content mt20"
          >
            <div class="form-item-title">
              {{ $t('高级选项') }}
            </div>

            <bk-form-item
              :label="$t('选择集群')"
              error-display-type="normal"
              ext-cls="form-item-cls mt20"
            >
              <bk-select
                v-model="formData.clusterName"
                class="form-input-width"
                searchable
              >
                <bk-option
                  v-for="option in clusterList"
                  :id="option"
                  :key="option"
                  :name="option"
                />
              </bk-select>
            </bk-form-item>
          </bk-form>
        </section>

        <!-- 源码&镜像 部署配置内容 -->
        <div
          class="mt20"
          v-if="formData.sourceOrigin === 'soundCode' && curStep === 2"
        >
          <collapseContent
            :title="$t('进程配置')"
            collapse-item-name="process"
            active-name="process"
          >
            <bk-alert type="info">
              <div slot="title">
                {{ $t('进程配置、钩子命令在 app_desc.yaml 文件中定义。') }}
                <a
                  target="_blank"
                  :href="GLOBAL.DOC.APP_DESC_DOC"
                  style="color: #3a84ff"
                >
                  {{ $t('应用描述文件') }}
                </a>
              </div>
            </bk-alert>
          </collapseContent>
        </div>

        <div
          class="mt20"
          v-if="formData.sourceOrigin === 'image' && curStep === 2"
        >
          <!-- 默认展开为编辑态 -->
          <collapseContent
            active-name="process"
            collapse-item-name="process"
            :title="$t('进程配置')"
          >
            <deploy-process
              ref="processRef"
              :cloud-form-data="formData"
              :is-create="isCreate"
            ></deploy-process>
          </collapseContent>

          <collapseContent
            active-name="hook"
            collapse-item-name="hook"
            :title="$t('部署前置命令')"
            class="mt20"
          >
            <deploy-hook
              ref="hookRef"
              :is-create="isCreate"
            ></deploy-hook>
          </collapseContent>
        </div>

        <div
          class="mt20 flex-row align-items-center"
          v-if="isBkDefaultCode"
        >
          <div
            v-if="curStep === 1"
            class="mr10"
            v-bk-tooltips="nextStepDisabledTips"
          >
            <!-- 代码仓库-未授权不能创建应用、租户下集群未配置时，不允许创建应用 -->
            <bk-button
              theme="primary"
              :disabled="isNextStepAllowed || !isAllowCreateApp"
              @click="handleNext"
            >
              {{ $t('下一步') }}
            </bk-button>
          </div>
          <div v-if="curStep === 2">
            <bk-button
              @click="handlePrev"
              class="mr10"
            >
              {{ $t('上一步') }}
            </bk-button>
            <bk-button
              theme="primary"
              class="mr10"
              :loading="formLoading"
              @click="handleCreateApp"
            >
              {{ $t('创建应用') }}
            </bk-button>
          </div>
          <bk-button @click="handleCancel">
            {{ $t('取消') }}
          </bk-button>
        </div>

        <div
          class="mt20 flex-row"
          v-else
        >
          <span v-bk-tooltips="disableCreateTips">
            <bk-button
              theme="primary"
              class="mr10"
              :disabled="!isAllowCreateApp"
              :loading="formLoading"
              @click="handleCreateApp"
            >
              {{ $t('创建应用') }}
            </bk-button>
          </span>
          <bk-button @click="handleCancel">
            {{ $t('取消') }}
          </bk-button>
        </div>
      </section>

      <!-- S-mart 应用 -->
      <create-smart-app
        v-if="curCodeSource === 'smart'"
        key="smart"
        :is-allow-create-app="isAllowCreateApp"
        :not-allow-create-message="notAllowCreateAppMessage"
      />
    </div>
  </section>
</template>
<script>
import { DEFAULR_LANG_NAME, DEFAULT_APP_SOURCE_CONTROL_TYPES } from '@/common/constants';
import { cloneDeep } from 'lodash';
import gitExtend from '@/components/ui/git-extend.vue';
import repoInfo from '@/components/ui/repo-info.vue';
import collapseContent from '@/views/dev-center/app/create-cloud-module/comps/collapse-content.vue';
import deployProcess from '@/views/dev-center/app/engine/cloud-deployment/deploy-process';
import deployHook from '@/views/dev-center/app/engine/cloud-deployment/deploy-hook';
import { TE_MIRROR_EXAMPLE } from '@/common/constants.js';
import defaultAppType from './default-app-type';
import createSmartApp from './smart';
import sidebarDiffMixin from '@/mixins/sidebar-diff-mixin';
import { mapGetters, mapState } from 'vuex';
import ExamplesDirectory from '@/components/examples-directory';
import PlatformCodeRepositoryForm from './comps/platform-code-repository-form.vue';
import CodeSourceSelector from './comps/code-source-selector.vue';
import UnauthorizedTips from './comps/unauthorized-tips.vue';

export default {
  components: {
    gitExtend,
    repoInfo,
    collapseContent,
    deployProcess,
    deployHook,
    defaultAppType,
    createSmartApp,
    ExamplesDirectory,
    PlatformCodeRepositoryForm,
    CodeSourceSelector,
    UnauthorizedTips,
  },
  mixins: [sidebarDiffMixin],
  data() {
    return {
      formData: {
        name: '', // 应用名称
        code: '', // 应用ID
        tenantMode: 'single',
        url: '', // 镜像仓库
        clusterName: '', // 集群名称
        sourceOrigin: 'soundCode', // 托管方式
        sourceInitTemplate: '', // 模版来源
        buildDir: '', // 构建目录
        sourceRepoUrl: '', // 代码仓库
        imageCredentialName: '', // 镜像名称
        imageCredentialUserName: '', // 镜像账号
        imageCredentialPassWord: '', // 镜像密码
        buildMethod: 'buildpack', // 构建方式
        dockerfilePath: '', // Dockerfile 路径
      },
      dockerfileData: {
        buildParams: [], // 构建参数
      },
      sourceOrigin: this.GLOBAL.APP_TYPES.NORMAL_APP,
      createSteps: [
        { title: this.$t('源码信息'), icon: 1 },
        { title: this.$t('部署配置'), icon: 2 },
      ],
      curStep: 1,
      buttonActive: '',
      languagesData: {},
      defaultlangName: DEFAULR_LANG_NAME, // 开发框架语言
      sourceControlTypes: DEFAULT_APP_SOURCE_CONTROL_TYPES, // 源码代码仓库
      sourceControlTypeItem: this.GLOBAL.DEFAULT_SOURCE_CONTROL,
      languagesList: [],
      sourceDirData: {
        error: '',
        value: '',
      },
      gitExtendConfig: {
        bk_gitlab: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('bk_gitlab'),
          repoList: [],
          selectedRepoUrl: '',
          authDocs: '',
        },
        tc_git: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('tc_git'),
          repoList: [],
          selectedRepoUrl: '',
          authDocs: this.GLOBAL.DOC.TC_GIT_AUTH,
        },
        github: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('github'),
          repoList: [],
          selectedRepoUrl: '',
          authDocs: '',
        },
        gitee: {
          isAuth: true,
          isLoading: false,
          alertText: '',
          authAddress: undefined,
          fetchMethod: this.generateFetchRepoListMethod('gitee'),
          repoList: [],
          selectedRepoUrl: '',
          authDocs: '',
        },
      },
      isCreate: true,
      localCloudAppData: {},
      repoData: {}, // svn代码库
      cloudAppProcessData: {
        image: '',
        name: 'web',
        command: [],
        args: [],
        memory: '256Mi',
        cpu: '500m',
        targetPort: 5000,
      },
      initCloudAppData: {},
      formLoading: false,
      advancedOptionsObj: {},
      regionChoose: 'ieod',
      rules: {
        code: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            max: 16,
            message: this.$t('请输入 3-16 字符的小写字母、数字、连字符(-)，以小写字母开头'),
            trigger: 'blur',
          },
          {
            validator: (val) => {
              const reg = this.isBkLesscode ? /^[a-z]{1,16}$/ : /^[a-z][a-z0-9-]{2,16}$/;
              return reg.test(val);
            },
            message: () =>
              this.isBkLesscode
                ? this.$t('格式不正确，由小写字母组成，长度小于 16 个字符')
                : this.$t('请输入 3-16 字符的小写字母、数字、连字符(-)，以小写字母开头'),
            trigger: 'blur',
          },
        ],
        name: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            max: 20,
            message: this.$t('请输入 1-20 字符的字母、数字、汉字'),
            trigger: 'blur',
          },
          {
            validator: (val) => {
              const reg = this.isBkLesscode ? /^[\u4e00-\u9fa5a-zA-Z0-9]{1,20}$/ : /^[a-zA-Z\d\u4e00-\u9fa5-]*$/;
              return reg.test(val);
            },
            message: () =>
              this.isBkLesscode
                ? this.$t('由汉字、英文字母、数字组成，长度不超过 20 个字符')
                : this.$t('由汉字、英文字母、数字、连字符（-）组成，长度不超过 20 个字符'),
            trigger: 'blur',
          },
        ],
        buildDir: [
          {
            validator(val) {
              const reg = /^((?!\.)[a-zA-Z0-9_./-]+|\s*)$/;
              return reg.test(val);
            },
            message: this.$t(
              '支持子目录、如 ab/test，允许字母、数字、点(.)、下划线(_)、和连接符(-)，但不允许以点(.)开头'
            ),
            trigger: 'blur',
          },
        ],
        url: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            regex: /^(?:([a-zA-Z0-9]+(?:[._-][a-zA-Z0-9]+)*(?::\d+)?)\/)?(?:([a-zA-Z0-9_.-]+)\/)*([a-zA-Z0-9_.-]+)$/,
            message: this.$t('请输入不包含标签(tag)的镜像仓库地址'),
            trigger: 'blur',
          },
        ],
        buildParams: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
        imageCredential: [
          {
            validator(val) {
              if (val === '') return true;
              const reg = /^[a-zA-Z0-9_]{0,40}$|^$/;
              return reg.test(val);
            },
            message: this.$t('以英文字母、数字或下划线(_)组成，不超过40个字'),
            trigger: 'blur',
          },
          {
            validator: this.validateCredentials,
            message: `${this.$t('请填写镜像凭证')} ${this.$t('名称')}`,
            trigger: 'blur',
          },
        ],
      },
      absolutePathRule: [
        {
          regex: /^(?!.*(^|\/|\\|)\.{1,2}($|\/|\\|)).*$/,
          message: this.$t('不支持填写相对路径'),
          trigger: 'blur',
        },
      ],
      curCodeSource: 'default',
      activeIndex: 1,
      isShowAdvancedOptions: false,
      pluginTmpls: [],
      curPluginTemplate: '',
      codeSourceId: 'default',
      curRepoDir: '',
      // 是否允许创建应用
      isAllowCreateApp: true,
      notAllowCreateAppMessage: this.$t(
        '当前用户无可用的应用集群，无法创建应用；请联系平台管理员添加集群或调整集群分配策略。'
      ),
      // 代码仓库配置
      codeRepositoryConfig: {
        type: 'existing',
        creationRepositories: [],
        formData: {},
      },
    };
  },
  computed: {
    ...mapState(['userFeature', 'platformFeature']),
    ...mapGetters(['tenantId', 'isShowTenant']),
    curSourceControl() {
      return this.sourceControlTypes.find((item) => item.value === this.sourceControlTypeItem);
    },
    cloudAppData() {
      return this.$store.state.cloudApi.cloudAppData;
    },
    clusterList() {
      // TODO（mh）目前先取 prod 的集群，后续前端按多租户设计稿开发时，需要分环境处理
      return this.advancedOptionsObj[this.regionChoose]?.['prod'] || [];
    },
    mirrorExamplePlaceholder() {
      return `${this.$t('请输入镜像仓库，如')}：${
        this.GLOBAL.CONFIG.MIRROR_EXAMPLE === 'nginx' ? this.GLOBAL.CONFIG.MIRROR_EXAMPLE : TE_MIRROR_EXAMPLE
      }`;
    },
    // 蓝鲸可视化平台
    isBkLesscode() {
      return this.curCodeSource === 'bkLesscode';
    },
    // 代码仓库
    isBkDefaultCode() {
      return this.curCodeSource === 'default';
    },
    // 蓝鲸插件
    isBkPlugin() {
      return this.activeIndex === 3;
    },
    // 蓝鲸开发
    isBkDevOps() {
      return this.activeIndex === 1;
    },
    curExtendConfig() {
      return this.gitExtendConfig[this.sourceControlTypeItem];
    },
    isNextStepAllowed() {
      return this.codeSourceId === 'default' && !this.curExtendConfig?.isAuth;
    },
    isDockerfile() {
      return this.formData.buildMethod === 'dockerfile';
    },
    // 根目录
    rootPath() {
      const { auth_method } = this.curSourceControl || {};
      const authPathMap = {
        oauth: this.formData.buildDir,
        basic: this.curRepoDir,
      };
      return authPathMap[auth_method] || '';
    },
    appendPath() {
      return this.isDockerfile ? this.formData.dockerfilePath || '' : '';
    },
    // 默认文件
    defaultFiles() {
      // 语言对应文件映射表
      const languageFileMap = {
        Python: 'requirements.txt',
        NodeJS: 'package.json',
        Go: 'go.mod',
      };
      // Dockerfile 构建方式直接返回固定文件
      if (this.isDockerfile) {
        return [{ name: 'requirements.txt' }];
      }
      // 获取当前语言类型
      const currentLanguage = this.isBkPlugin
        ? this.pluginTmpls.find((v) => v.name === this.curPluginTemplate)?.language
        : this.buttonActive || 'Python';

      return [{ name: languageFileMap[currentLanguage] }];
    },
    // 创建应用禁用 tips
    disableCreateTips() {
      return {
        content: this.notAllowCreateAppMessage,
        disabled: this.isAllowCreateApp,
        width: 285,
      };
    },
    // 下一步禁用 tips
    nextStepDisabledTips() {
      if (this.isAllowCreateApp) {
        return { content: this.$t('请先授权代码源，然后选代码仓库'), disabled: !this.isNextStepAllowed };
      }
      return this.disableCreateTips;
    },
    // 是否为平台自动创建
    isCreatedByPlatform() {
      return this.codeRepositoryConfig.type === 'platform';
    },
  },
  watch: {
    'formData.sourceOrigin'(value) {
      this.curStep = 1;
      if (value === 'image') {
        this.sourceOrigin = this.GLOBAL.APP_TYPES.CNATIVE_IMAGE; // 6 仅镜像的云原生应用
        this.createSteps = [
          { title: this.$t('镜像信息'), icon: 1 },
          { title: this.$t('部署配置'), icon: 2 },
        ];
      } else if (value === 'soundCode') {
        this.sourceOrigin = this.GLOBAL.APP_TYPES.NORMAL_APP; // 1
        this.createSteps = [
          { title: this.$t('源码信息'), icon: 1 },
          { title: this.$t('部署配置'), icon: 2 },
        ];
      }
      this.$refs.formImageRef?.clearError();
    },

    cloudAppData: {
      handler(value) {
        if (!Object.keys(value).length) {
          // 没有应用编排数据
          this.initCloudAppDataFunc();
        }
      },
      immediate: true,
    },

    'formData.code'(value) {
      if (!this.initCloudAppData.metadata) {
        this.initCloudAppData.metadata = {};
      }
      // 如果有cloudAppData 则将cloudAppData赋值给initCloudAppData
      if (Object.keys(this.cloudAppData).length) {
        this.initCloudAppData = cloneDeep(this.cloudAppData);
      }
      this.initCloudAppData.metadata.name = value;
      this.localCloudAppData = cloneDeep(this.initCloudAppData);

      this.$store.commit('cloudApi/updateCloudAppData', this.initCloudAppData);
    },
    isShowAdvancedOptions(value) {
      this.$store.commit('createApp/updateAdvancedOptions', value);
    },
    'platformFeature.REGION_DISPLAY'() {
      this.getPluginTmpls();
    },
  },
  mounted() {
    this.init();
  },
  methods: {
    async init() {
      await Promise.all([this.fetchLanguageInfo(), this.fetchSourceControlTypesData(), this.fetchAdvancedOptions()]);
      this.getPluginTmpls();
      // 收集依赖
      const data = this.collectDependencies();
      this.initSidebarFormData(data);
    },
    handleSelected(item, key) {
      this.buttonActive = key;
      this.languagesList = item;
      this.formData.sourceInitTemplate = this.languagesList[0].name;
    },

    // 收集基本表单依赖
    collectDependencies() {
      const data = {
        code: this.formData.code,
        name: this.formData.name,
        source_config: {
          source_init_template: this.formData.sourceInitTemplate,
          source_control_type: this.sourceControlTypeItem,
          source_repo_url: this.formData.sourceRepoUrl,
          source_dir: this.formData.buildDir || '',
        },
      };
      if (
        this.sourceOrigin === this.GLOBAL.APP_TYPES.NORMAL_APP &&
        ['bare_git', 'bare_svn'].includes(this.sourceControlTypeItem)
      ) {
        data.source_config.source_repo_url = this.repoData.url;
        data.source_config.source_repo_auth_info = {
          username: this.repoData.account,
          password: this.repoData.password,
        };
        data.source_config.source_dir = this.repoData.sourceDir;
      }
      return data;
    },

    // 设置语言顺序
    prioritizeKeys(obj, keysToPrioritize) {
      // 优先排序后的对象
      const prioritizedObj = {};
      keysToPrioritize.forEach((key) => {
        if (Object.prototype.hasOwnProperty.call(obj, key)) {
          prioritizedObj[key] = obj[key];
        }
      });
      for (const key in obj) {
        if (!keysToPrioritize.includes(key)) {
          prioritizedObj[key] = obj[key];
        }
      }
      return prioritizedObj;
    },

    // 获取模版来源
    async fetchLanguageInfo() {
      try {
        const res = await this.$store.dispatch('module/getLanguageInfo');
        const regionChoose = Object.keys(res) || [];
        this.regionChoose = regionChoose[0] || 'ieod';
        const languages = res[this.regionChoose]?.languages || {};
        this.languagesData = this.prioritizeKeys(languages, ['Python', 'NodeJS']);
        const languagesKeysData = Object.keys(this.languagesData) || [];
        this.buttonActive = languagesKeysData[0] || 'Python';
        this.languagesList = this.languagesData[this.buttonActive];
        this.formData.sourceInitTemplate = this.languagesList[0].name;
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isLoading = false;
      }
    },

    // 获取代码源仓库信息
    async fetchSourceControlTypesData() {
      this.$store.dispatch('fetchAccountAllowSourceControlType', {}).then((res) => {
        this.sourceControlTypes = res;
        this.sourceControlTypes = this.sourceControlTypes.map((e) => {
          e.imgSrc = e.value;
          if (e.value === 'bare_svn') {
            e.imgSrc = 'bk_svn';
          }
          return e;
        });

        // 判断是否提供选择仓库类型
        this.codeRepositoryConfig.creationRepositories = res.filter((item) => item.repo_creation_enabled);

        this.sourceControlTypeItem =
          this.sourceControlTypes.find((item) => item.imgSrc === this.sourceControlTypeItem)?.imgSrc ??
          this.sourceControlTypes[0]?.imgSrc;
        const sourceControlTypeValues = this.sourceControlTypes.map((item) => item.value);
        sourceControlTypeValues.forEach((item) => {
          if (!Object.keys(this.gitExtendConfig).includes(item)) {
            this.$set(
              this.gitExtendConfig,
              item,
              cloneDeep({
                isAuth: true,
                isLoading: false,
                alertText: '',
                authAddress: undefined,
                fetchMethod: this.generateFetchRepoListMethod(item),
                repoList: [],
                selectedRepoUrl: '',
              })
            );
          }
        });
        // 在这几种类型里面需要请求
        Object.keys(this.gitExtendConfig).forEach((key) => {
          const config = this.gitExtendConfig[key];
          if (
            key === this.sourceControlTypeItem &&
            ['bk_gitlab', 'tc_git', 'github', 'gitee'].includes(this.sourceControlTypeItem)
          ) {
            config.fetchMethod();
          }
        });
      });
    },

    // 获取高级选项 集群列表
    async fetchAdvancedOptions() {
      try {
        const res = await this.$store.dispatch('createApp/getOptions');

        // 提取高级选项信息
        const { adv_region_clusters = [], allow_adv_options } = res;

        // 获取对应 region 下的集群信息
        const curRegionClusters = adv_region_clusters.find((v) => v.region === this.GLOBAL.CONFIG.REGION_CHOOSE);
        const hasRequiredClusters = (clusters) => clusters?.stag?.length > 0 && clusters?.prod?.length > 0;
        // 没有配置集群，无法创建应用
        this.isAllowCreateApp = curRegionClusters
          ? hasRequiredClusters(curRegionClusters?.env_cluster_names || {})
          : false;

        // 高级选项是否可用
        this.isShowAdvancedOptions = allow_adv_options;

        // Region 的集群信息
        adv_region_clusters.forEach((item) => {
          if (!this.advancedOptionsObj.hasOwnProperty(item.region)) {
            this.$set(this.advancedOptionsObj, item.region, item.env_cluster_names);
          }
        });
      } catch (e) {
        // 请求接口报错时则不显示高级选项
        this.isShowAdvancedOptions = false;
      }
    },

    generateFetchRepoListMethod(sourceControlTypeItem) {
      // 根据不同的 sourceControlTypeItem 生成对应的 fetchRepoList 方法
      return async () => {
        const config = this.gitExtendConfig[sourceControlTypeItem];
        try {
          config.isLoading = true;
          const resp = await this.$store.dispatch('getRepoList', { sourceControlType: sourceControlTypeItem });
          config.repoList = resp.results.map((repo) => ({ name: repo.fullname, id: repo.http_url_to_repo }));
          config.isAuth = true;
        } catch (e) {
          const resp = e.response;
          config.isAuth = false;
          if (resp.status === 403 && resp.data.result) {
            config.authAddress = resp.data.address;
            config.authDocs = resp.data.auth_docs;
          }
        } finally {
          config.isLoading = false;
        }
      };
    },

    // 点击源码仓库
    changeSourceControl(item) {
      this.sourceDirData.error = false;
      this.sourceDirData.value = '';
      this.sourceControlTypeItem = item.value;
      const curGitConfig = this.gitExtendConfig[this.sourceControlTypeItem];
      if (
        curGitConfig &&
        curGitConfig.repoList.length < 1 &&
        ['bk_gitlab', 'tc_git', 'github', 'gitee'].includes(this.sourceControlTypeItem)
      ) {
        curGitConfig.fetchMethod();
      }
    },

    // 下一步按钮
    async handleNext() {
      try {
        await this.$refs.formBaseRef.validate();
        await this.$refs?.formImageRef?.validate();
        await this.$refs?.formSourceRef?.validate();
        await this.$refs?.repoInfo?.valid();
        // 构建参数校验
        const flag = await this.buildParamsValidate();
        if (!flag) {
          return;
        }
        if (this.sourceOrigin === this.GLOBAL.APP_TYPES.NORMAL_APP) {
          // 普通应用
          await this.$refs?.extend?.valid(); // 代码仓库
          this.formData.sourceRepoUrl = null;
          switch (this.sourceControlTypeItem) {
            case 'bk_gitlab':
            case 'github':
            case 'gitee':
            case 'tc_git':
              // eslint-disable-next-line no-case-declarations
              const config = this.gitExtendConfig[this.sourceControlTypeItem];
              this.formData.sourceRepoUrl = config.selectedRepoUrl;

              break;
            case 'bk_svn':
            default:
              this.formData.sourceRepoUrl = undefined;
              break;
          }
        }
        // 获取新建代码仓库数据
        if (this.isCreatedByPlatform) {
          this.codeRepositoryConfig.formData = this.$refs.newCodeRepositoryForm?.getFromData();
        }
        this.repoData = this.$refs?.repoInfo?.getData() ?? {};
        this.curStep = 2;
        this.$nextTick(() => {
          // 默认编辑态
          this.$refs.processRef?.handleEditClick();
          this.$refs.hookRef?.handleEditClick();
        });
      } catch (e) {
        console.error(e);
      }
    },

    // 上一步
    handlePrev() {
      this.curStep = 1;
    },

    // 处理取消
    async handleCancel() {
      // 内容变更输入弹窗提示
      const isSwitching = await this.handleBeforeFunction();
      if (!isSwitching) {
        return;
      }
      this.$refs?.processRef?.handleCancel();
      this.initCloudAppData = cloneDeep(this.localCloudAppData);
      this.$store.commit('cloudApi/updateHookPageEdit', false);
      this.$store.commit('cloudApi/updateProcessPageEdit', false);
      this.$router.push({
        name: 'myApplications',
      });
    },

    // 钩子命令校验
    async handleHookValidator() {
      if (this.$refs.hookRef) {
        return await this.$refs.hookRef?.handleValidator();
      }
      return true;
    },

    // 参数区分：已有代码仓库 / 由平台创建代码仓库
    getRepositoryParams() {
      if (this.isCreatedByPlatform) {
        return {
          auto_create_repo: true,
          write_template_to_repo: true,
          ...this.codeRepositoryConfig.formData,
        };
      }
      return {
        source_repo_url: this.formData.sourceRepoUrl,
      };
    },

    // 创建应用
    async handleCreateApp() {
      if (this.cloudAppData.spec?.hooks) {
        const isVerificationPassed = await this.handleHookValidator();
        if (!isVerificationPassed) {
          return;
        }
      }

      // 选择了lesscode代码来源
      if (this.sourceOrigin === this.GLOBAL.APP_TYPES.LESSCODE_APP) {
        await this.$refs.formBaseRef.validate();
      }
      this.formLoading = true;
      const params = {
        is_plugin_app: this.isBkPlugin,
        region: this.regionChoose,
        code: this.formData.code,
        name: this.formData.name,
        // 租户模式
        ...(this.isShowTenant && { app_tenant_mode: this.formData.tenantMode }),
        source_config: {
          source_init_template: this.isBkPlugin ? this.curPluginTemplate : this.formData.sourceInitTemplate,
          source_control_type: this.sourceControlTypeItem,
          ...this.getRepositoryParams(),
          source_origin: this.sourceOrigin,
          source_dir: this.formData.buildDir || '',
        },
        bkapp_spec: {
          // 构建方式
          build_config: {
            build_method: this.formData.buildMethod,
          },
        },
      };

      // dockerfile 构建方式
      if (this.formData.buildMethod === 'dockerfile') {
        // 构建参数
        const dockerBuild = {};
        this.dockerfileData.buildParams.forEach((item) => {
          dockerBuild[item.name] = item.value;
        });
        params.bkapp_spec.build_config = {
          build_method: 'dockerfile',
          dockerfile_path: this.formData.dockerfilePath || null,
          docker_build_args: dockerBuild,
        };
        delete params.source_config.source_init_template;
      }

      // 仅镜像
      if (this.formData.sourceOrigin === 'image') {
        params.bkapp_spec.build_config = {
          build_method: 'custom_image',
          image_repository: this.formData.url,
        };
        const processData = await this.$refs?.processRef?.handleSave();
        const hookData = await this.$refs?.hookRef?.handleSave();
        if (!processData || !hookData) return;
        hookData.type = 'pre-release-hook';
        params.bkapp_spec.processes = processData;
        if (hookData.enabled) {
          params.bkapp_spec.hook = hookData;
        }
      }

      // 集群名称
      if (this.formData.clusterName) {
        params.advanced_options = {
          // TODO（mh）暂时兼容前端页面组件，在按新的多租户设计稿修改后，需使用具体字段
          env_cluster_names: {
            stag: this.formData.clusterName,
            prod: this.formData.clusterName,
          },
        };
      }

      if (
        this.sourceOrigin === this.GLOBAL.APP_TYPES.NORMAL_APP &&
        ['bare_git', 'bare_svn'].includes(this.sourceControlTypeItem)
      ) {
        params.source_config.source_repo_url = this.repoData.url;
        params.source_config.source_repo_auth_info = {
          username: this.repoData.account,
          password: this.repoData.password,
        };
        params.source_config.source_dir = this.repoData.sourceDir;
      }

      if (this.sourceOrigin === this.GLOBAL.APP_TYPES.CNATIVE_IMAGE) {
        // 仅镜像
        params.source_config = {
          source_origin: this.sourceOrigin,
        };
        // 镜像凭证任意有一个值都需要image_credentials字段，如果都没有这不需要此字段
        if (
          this.formData.imageCredentialName ||
          this.formData.imageCredentialUserName ||
          this.formData.imageCredentialPassWord
        ) {
          params.bkapp_spec.build_config.image_credential = {};
        }
        // 仅镜像需要镜像凭证信息
        if (this.formData.imageCredentialName) {
          params.bkapp_spec.build_config.image_credential.name = this.formData.imageCredentialName;
        }
        if (this.formData.imageCredentialUserName) {
          params.bkapp_spec.build_config.image_credential.username = this.formData.imageCredentialUserName;
        }
        if (this.formData.imageCredentialPassWord) {
          params.bkapp_spec.build_config.image_credential.password = this.formData.imageCredentialPassWord;
        }
        // params.manifest = {
        //   ...this.cloudAppData,
        // };
        params.source_config.source_repo_url = this.formData.url; // 镜像
      }

      // lesscode应用
      if (this.sourceOrigin === this.GLOBAL.APP_TYPES.LESSCODE_APP) {
        const languageName = this.languagesData.NodeJS[0]?.name;
        params.source_config = {
          source_init_template: languageName,
          source_origin: this.sourceOrigin,
        };
      }

      // 新建代码仓库（由平台自动创建）过滤 source_repo_url
      if (this.isCreatedByPlatform) {
        params.source_config.write_template_to_repo = !!params.source_config.source_init_template;
        delete params.source_config.source_repo_url;
      }

      try {
        const res = await this.$store.dispatch('cloudApi/createCloudApp', {
          appCode: this.appCode,
          data: params,
        });

        const objectKey = `CloundSourceInitResult${Math.random().toString(36)}`;
        if (res.source_init_result) {
          localStorage.setItem(objectKey, JSON.stringify(res.source_init_result.extra_info));
        }

        const path = `/developer-center/apps/${res.application.code}/create/${this.sourceControlTypeItem}/success`;
        this.$router.push({
          path,
          query: {
            method: params.bkapp_spec.build_config.build_method,
            template: params.source_config.source_init_template,
            type: this.codeRepositoryConfig.type,
            objectKey,
          },
        });
      } catch (e) {
        this.handleAppCreationSpecificErrors(e);
      } finally {
        this.formLoading = false;
      }
    },

    // 处理应用创建过程中的特定错误
    handleAppCreationSpecificErrors(error) {
      const { code, detail, message } = error;

      // 特殊错误代码集合
      const errorCodeList = [
        'REPO_ACCESS_TOKEN_PERM_DENIED',
        'REPO_DEFAULT_SCOPE_PERMISSION_ERROR',
        'CREATE_APP_FAILED',
      ];

      if (errorCodeList.includes(code)) {
        this.handlePrev();
        if (code !== 'CREATE_APP_FAILED') {
          this.showCodeAuthModal(code, detail || message);
          return;
        }
      }

      this.catchErrorHandler(error);
    },

    /**
     * 显示代码授权弹窗
     * @param {string} code - 错误代码
     * @param {string} message - 错误消息
     */
    showCodeAuthModal(code, message) {
      const h = this.$createElement;
      const { href: authPageUrl } = this.$router.resolve({ name: 'serviceCode' });

      const messageContent = h(
        'div',
        {
          class: 'flex-row justify-content-between',
          style: { width: '100%' },
        },
        [message, this.createAuthLinkButton(h, authPageUrl)]
      );

      this.$paasMessage({
        theme: 'error',
        message: messageContent,
        delay: 0, // 消息不自动关闭
        extCls: 'custom-message-close-icon-ml5',
      });
    },

    /**
     * 创建授权链接按钮
     * @param {Function} h - createElement 函数
     * @param {string} authPageUrl - 授权页面URL
     */
    createAuthLinkButton(h, authPageUrl) {
      return h(
        'div',
        {
          style: {
            color: '#3a84ff',
            cursor: 'pointer',
          },
          on: {
            click: () => window.open(authPageUrl, '_blank'),
          },
        },
        [h('i', { class: 'paasng-icon paasng-jump-link mr5' }), this.$t('查看授权信息')]
      );
    },

    // 初始化应用编排数据
    initCloudAppDataFunc() {
      this.initCloudAppData = {
        apiVersion: 'paas.bk.tencent.com/v1alpha2',
        kind: 'BkApp',
        metadata: { name: this.formData.code },
        spec: {
          build: {
            image: this.formData.url.trim(), // 镜像信息-镜像仓库
            imageCredentialsName: this.formData.imageCredentialName, // 镜像信息-镜像凭证-名称
          },
          processes: [this.cloudAppProcessData],
        },
      };
      this.localCloudAppData = cloneDeep(this.initCloudAppData);
      this.$store.commit('cloudApi/updateCloudAppData', this.initCloudAppData);
    },

    // 构建参数校验
    async buildParamsValidate() {
      let flag = true;
      if (!this.dockerfileData.buildParams.length) {
        return flag;
      }
      // eslint-disable-next-line no-restricted-syntax
      for (const index in this.dockerfileData.buildParams) {
        try {
          await this.$refs[`name-${index}`][0]?.validate().finally(async () => {
            await this.$refs[`value-${index}`][0]?.validate();
          });
        } catch (error) {
          flag = false;
        }
      }
      return flag;
    },

    // 新建构建参数
    addBuildParams() {
      this.dockerfileData.buildParams.push({
        name: '',
        value: '',
      });
    },

    removeBuildParams(index) {
      this.dockerfileData.buildParams.splice(index, 1);
    },

    handleChangeBuildMethod(value) {
      this.formData.sourceOrigin = value === 'image' ? 'image' : 'soundCode';
    },

    // 切换应用类型
    handleSwitchAppType(codeSource) {
      this.codeSourceId = codeSource;
      this.activeIndex = 1;
      this.curStep = 1;
      this.$refs.formBaseRef?.clearError();
      this.curCodeSource = codeSource;
      this.formData.buildMethod = 'buildpack';
      this.formData.sourceOrigin = 'soundCode';
      this.$nextTick(() => {
        // 蓝鲸可视化平台推送的源码包
        if (codeSource === 'bkLesscode') {
          this.regionChoose = this.GLOBAL.CONFIG.REGION_CHOOSE;
          this.handleCodeTypeChange(2);
        } else if (codeSource === 'default') {
          // 普通应用
          this.handleCodeTypeChange(1);
        } else if (codeSource === 'image') {
          this.curCodeSource = 'default';
          this.formData.sourceOrigin = codeSource;
          this.formData.buildMethod = codeSource;
          // 云原生仅镜像
          this.sourceOrigin === this.GLOBAL.APP_TYPES.CNATIVE_IMAGE;
        }
      });
    },

    // 模版来源切换
    handleCodeTypeChange(payload) {
      this.activeIndex = payload;
      if (payload === this.GLOBAL.APP_TYPES.NORMAL_APP || payload === this.GLOBAL.APP_TYPES.LESSCODE_APP) {
        this.sourceOrigin = payload;
      } else {
        this.sourceOrigin = this.GLOBAL.APP_TYPES.NORMAL_APP;
      }
    },

    async handleBeforeFunction() {
      const data = this.collectDependencies();
      return this.$isSidebarClosed(JSON.stringify(data));
    },

    // 获取蓝鲸插件模板信息
    async getPluginTmpls() {
      try {
        const res = await this.$store.dispatch('cloudApi/getPluginTmpls');
        this.curPluginTemplate = res[0]?.name || '';
        this.pluginTmpls = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 镜像凭证是否必填校验
    validateCredentials(value) {
      const { imageCredentialName, imageCredentialUserName, imageCredentialPassWord } = this.formData;
      // 如果三个都为空通过
      if (!imageCredentialName && !imageCredentialUserName && !imageCredentialPassWord) {
        return true;
      }
      return !!value;
    },

    // 镜像凭证填写校验
    getImageCredentialRule(msg) {
      return [
        {
          validator: this.validateCredentials,
          message: `${this.$t('请填写镜像凭证')} ${this.$t(msg)}`,
          trigger: 'blur',
        },
      ];
    },
  },
};
</script>
<style lang="scss" scoped>
@import './cloud.scss';
</style>
