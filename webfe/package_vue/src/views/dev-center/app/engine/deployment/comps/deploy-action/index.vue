<template lang="html">
  <paas-content-loader
    :is-loading="isLoading"
    placeholder="deploy-inner-loading"
    :offset-top="20"
    :offset-left="20"
    class="deploy-action-box"
  >
    <!-- isWatchDeploying: {{isWatchDeploying}} ||
        isDeploySuccess: {{isDeploySuccess}} ||
        isDeployFail: {{isDeployFail}} ||
        isDeployInterrupted: {{isDeployInterrupted}} ||
        isDeployInterrupting: {{isDeployInterrupting}} ||
        isScrollFixed: {{isScrollFixed}} -->
    <template v-if="isWatchDeploying || isWatchOfflineing || isDeploySuccess || isDeployFail">
      <!-- 部署中 -->
      <div
        v-if="isWatchDeploying"
        id="deploying-box"
        class="summary-box"
        :style="scrollStyle.summary"
      >
        <div class="wrapper primary">
          <div class="fl">
            <round-loading
              size="small"
              ext-cls="deploy-round-loading"
            />
          </div>
          <section style="position: relative; margin-left: 60px">
            <p class="deploy-pending-text">
              {{ $t('正在部署中...') }}
            </p>
            <p class="deploy-text-wrapper">
              <span
                v-if="!isLesscodeApp"
                class="branch-text"
              >
                {{ $t('分支：') }} {{ branchSelection.split(':')[1] }}
              </span>
              <span class="version-text">{{ $t('版本：') }} {{ curDeployId }}</span>
              <span
                v-if="deployTotalTime"
                class="time-text"
              >
                {{ $t('耗时：') }} {{ deployTotalTimeDisplay }}
              </span>
            </p>
            <section
              v-if="appearDeployState.includes('build') || appearDeployState.includes('release')"
              class="action-wrapper"
            >
              <bk-button
                :text="true"
                @click="stopDeploy"
              >
                {{ $t('停止部署') }}
              </bk-button>
            </section>
          </section>
        </div>
      </div>

      <!-- 下架中 -->
      <div
        v-if="isWatchOfflineing"
        id="offlineing-box"
        class="summary-box mb20"
        :style="scrollStyle.summary"
      >
        <div class="wrapper primary">
          <div class="fl">
            <round-loading
              size="small"
              ext-cls="deploy-round-loading"
            />
          </div>
          <section style="margin-left: 60px">
            <p class="deploy-pending-text">
              {{ $t('正在下架中...') }}
            </p>
            <p class="deploy-text-wrapper">
              <span
                v-if="!isLesscodeApp"
                class="branch-text"
              >
                {{ $t('分支：') }} {{ deploymentInfo.repo.name }}
              </span>
              <span class="version-text">{{ $t('版本：') }} {{ deploymentInfo.repo.version }}</span>
            </p>
          </section>
        </div>
      </div>

      <!-- 部署失败 -->
      <div
        v-if="isDeployFail"
        id="fail-box"
        class="summary-box"
        :style="scrollStyle.summary"
      >
        <div class="wrapper danger">
          <div class="fl">
            <span class="paasng-icon paasng-info-circle-shape" />
          </div>
          <section style="position: relative; margin-left: 50px">
            <p class="deploy-pending-text">
              {{ $t('部署失败') }}
            </p>
            <p class="deploy-text-wrapper">
              <span class="reason mr5">{{ curDeployResult.possible_reason }}</span>
              <template v-if="curDeployResult.result === 'failed'">
                <span
                  v-for="(help, index) in curDeployResult.error_tips.helpers"
                  :key="index"
                >
                  <a
                    :href="help.link"
                    target="_blank"
                    class="mr10"
                  >
                    {{ help.text }}
                  </a>
                </span>
              </template>
            </p>
            <section class="action-wrapper">
              <bk-button
                theme="danger"
                ext-cls="paas-deploy-failed-btn"
                outline
                @click="handleDeploy"
              >
                {{ $t('重新部署') }}
              </bk-button>
              <bk-button
                style="margin-left: 6px"
                theme="danger"
                ext-cls="paas-deploy-failed-btn"
                outline
                @click="handleFailCallback"
              >
                {{ $t('返回') }}
              </bk-button>
            </section>
          </section>
        </div>
      </div>

      <!-- 部署成功 -->
      <div
        v-if="isDeploySuccess"
        id="success-box"
        class="summary-box"
        :style="scrollStyle.summary"
      >
        <div class="wrapper success">
          <div class="fl">
            <span class="paasng-icon paasng-check-circle-shape" />
          </div>
          <section style="position: relative; margin-left: 50px">
            <div class="deploy-pending-text">
              <div v-if="environment === 'stag'">
                {{ $t('应用部署成功') }}
              </div>
              <div v-else-if="environment === 'prod'">
                <p v-if="appMarketPublished && curAppModule.is_default">
                  {{ $t('应用部署成功，已发布至蓝鲸应用市场') }}
                </p>
                <p v-else-if="!appMarketPublished && curAppModule.is_default">
                  {{ $t('应用部署成功，未发布至蓝鲸应用市场') }}
                  <router-link
                    class="ml5 fn"
                    :to="{ name: 'appMarket', params: { id: appCode } }"
                  >
                    {{ $t('去设置') }}
                  </router-link>
                </p>
                <p v-else>
                  {{ $t('应用部署成功') }}
                </p>
              </div>
            </div>
            <p class="deploy-text-wrapper">
              <span
                v-if="!isLesscodeApp"
                class="branch-text"
              >
                {{ $t('分支：') }} {{ branchSelection.split(':')[1] }}
              </span>
              <span class="version-text">{{ $t('版本：') }} {{ curDeployId }}</span>
              <span
                v-if="deployTotalTime"
                class="time-text"
              >
                {{ $t('耗时：') }} {{ deployTotalTimeDisplay }}
              </span>
            </p>
            <section class="action-wrapper">
              <bk-button
                theme="success"
                ext-cls="paas-deploy-success-btn"
                outline
                @click="handleOpenLink"
              >
                {{ $t('访问') }}
              </bk-button>
              <bk-button
                style="margin-left: 6px"
                theme="success"
                ext-cls="paas-deploy-success-btn"
                outline
                @click="handleSuccessCallback"
              >
                {{ $t('返回') }}
              </bk-button>
            </section>
          </section>
        </div>
      </div>
    </template>

    <template v-else-if="isDeployInterrupted || isDeployInterrupting">
      <!-- 停止部署 -->
      <div
        v-if="isDeployInterrupting"
        id="deploying-box"
        class="summary-box"
        :style="scrollStyle.summary"
      >
        <div class="wrapper warning">
          <div class="fl">
            <round-loading
              size="small"
              ext-cls="deploy-round-loading"
            />
          </div>
          <section style="position: relative; margin-left: 60px">
            <p class="deploy-pending-text">
              {{ $t('部署停止中...') }}
            </p>
            <p class="deploy-text-wrapper">
              <span
                v-if="!isLesscodeApp"
                class="branch-text"
              >
                {{ $t('分支：') }} {{ branchSelection.split(':')[1] }}
              </span>
              <span class="version-text">{{ $t('版本：') }} {{ curDeployId }}</span>
              <span
                v-if="deployTotalTime"
                class="time-text"
              >
                {{ $t('耗时：') }} {{ deployTotalTimeDisplay }}
              </span>
            </p>
            <section
              v-if="appearDeployState.includes('build') || appearDeployState.includes('release')"
              class="action-wrapper"
            >
              <bk-button
                :text="true"
                disabled
              >
                {{ $t('停止中') }}
              </bk-button>
            </section>
          </section>
        </div>
      </div>
      <div
        v-if="isDeployInterrupted"
        id="deploying-box"
        class="summary-box"
        :style="scrollStyle.summary"
      >
        <div class="wrapper warning">
          <div class="fl">
            <span
              style="position: relative; top: 4px; font-size: 32px"
              class="paasng-icon paasng-info-circle-shape"
            />
          </div>
          <section style="position: relative; margin-left: 50px">
            <p class="deploy-pending-text">
              {{ $t('部署已中断') }}
            </p>
            <p class="deploy-text-wrapper">
              <span>
                {{ $t('由') }} {{ lastDeploymentInfo.operator.username }} {{ $t('于') }}
                {{ lastDeploymentInfo.created }} {{ $t(' 手动停止部署') }}
              </span>
              <span>
                <bk-button
                  style="vertical-align: top; font-size: 12px; margin-left: 20px"
                  :text="true"
                  @click="goProcessView"
                >
                  {{ $t('查看进程状态') }}
                </bk-button>
              </span>
            </p>
            <section class="action-wrapper">
              <bk-button
                theme="warning"
                class="paas-deploy-interrupt-btn"
                outline
                @click="handleDeploy"
              >
                {{ $t('重新部署') }}
              </bk-button>
              <bk-button
                style="margin-left: 6px"
                class="paas-deploy-interrupt-btn"
                theme="warning"
                outline
                @click="handleFailCallback"
              >
                {{ $t('返回') }}
              </bk-button>
            </section>
          </section>
        </div>
      </div>
    </template>

    <template v-else>
      <!-- 最近部署失败 或者 停止部署 -->
      <div
        v-if="
          lastDeploymentInfo && (lastDeploymentInfo.status === 'failed' || lastDeploymentInfo.status === 'interrupted')
        "
        class="summary-box status"
        style="position: relative; z-index: 1"
      >
        <div class="wrapper default-box warning">
          <div class="fl">
            <span class="paasng-icon paasng-paas-remind-fill mr5 f16" />
          </div>
          <div class="fl mr25">
            {{ $t('最近部署：') }}
            <span>{{ $t('版本：') }} {{ lastDeploymentInfo.repo.version }}，</span>
            <span v-if="!isLesscodeApp">{{ $t('分支：') }} {{ lastDeploymentInfo.repo.name }}，</span>
            <span>
              {{ $t('由') }} {{ lastDeploymentInfo.operator.username }} {{ $t('于') }} {{ lastDeploymentInfo.created }}
              <template>{{ lastDeploymentInfo.status === 'failed' ? $t('部署失败') : $t('手动停止部署') }}</template>
            </span>
          </div>

          <router-link
            class="fr mr5"
            :to="{
              name: 'appDeployForHistory',
              params: { id: appCode, moduleId: curModuleId },
              query: { deployId: lastDeploymentInfo.id },
            }"
          >
            {{ $t('查看部署日志') }}
          </router-link>
        </div>
      </div>

      <!-- 已经部署成功 -->
      <div
        v-if="deploymentInfo"
        class="summary-box status"
        :style="{ 'margin-top': lastDeploymentInfo && lastDeploymentInfo.status === 'failed' ? '-5px' : '0' }"
      >
        <div class="wrapper default-box">
          <div class="fl mr25">{{ $t('当前版本') }}： {{ deploymentInfo.repo.version }}</div>
          <div
            v-if="!isLesscodeApp"
            class="fl"
          >
            {{ $t('分支：') }} {{ deploymentInfo.repo.name }}
          </div>
          <div class="span fl" />
          <div class="fl">
            {{ $t('由') }} {{ deploymentInfo.operator && deploymentInfo.operator.username }} {{ $t('于') }}
            {{ deploymentInfo.created }} {{ isAppOffline ? $t('下架') : $t('部署') }}
          </div>

          <bk-dropdown-menu
            v-if="!isAppOffline"
            ref="dropdown"
            class="fr"
            style="height: auto"
          >
            <div
              slot="dropdown-trigger"
              class="dropdown-trigger-btn"
            >
              <span class="paasng-icon paasng-icon-more f16" />
            </div>
            <ul
              slot="dropdown-content"
              class="bk-dropdown-list"
            >
              <li>
                <a
                  href="javascript:;"
                  style="width: 66px"
                  @click="handleOfflineApp"
                >
                  {{ $t('下架') }}
                </a>
              </li>
            </ul>
          </bk-dropdown-menu>
          <a
            v-if="exposedLink"
            class="fr mr10"
            :href="exposedLink"
            target="_blank"
          >
            {{ $t('点击访问') }}
          </a>
        </div>
      </div>

      <!-- 未部署过 -->
      <div
        v-else-if="!lastDeploymentInfo"
        class="summary-box status tc"
      >
        <div class="wrapper not-deploy f14">
          {{ $t('暂未部署') }}
        </div>
      </div>

      <div class="deploy-action mt mt20">
        <div v-if="deployPreparations.all_conditions_matched">
          <strong class="f14 mb10">{{ $t('选择部署') }} {{ isLesscodeApp ? $t('版本') : $t('分支') }}</strong>
          <div class="branch">
            <bk-select
              v-model="branchSelection"
              :placeholder="$t('请选择')"
              style="width: 420px; display: inline-block; vertical-align: middle"
              :popover-min-width="420"
              :clearable="false"
              :searchable="true"
              :loading="isBranchesLoading"
              :empty-text="branchEmptyText"
              @selected="handleBranchSelect"
            >
              <bk-option-group
                v-for="(branch, index) in branchList"
                :key="index"
                class="option-group"
                :name="branch.displayName"
              >
                <bk-button
                  ext-cls="paas-branch-btn"
                  theme="primary"
                  text
                  @click="getModuleBranches"
                >
                  {{ $t('刷新') }}
                </bk-button>
                <bk-option
                  v-for="option in branch.children"
                  :id="option.id"
                  :key="option.id"
                  :name="option.text"
                />
              </bk-option-group>
              <div
                v-if="curAppModule.repo && curAppModule.repo.type === 'bk_svn'"
                slot="extension"
                style="cursor: pointer"
                @click="handleCreateBranch"
              >
                <i class="bk-icon icon-plus-circle mr5" />
                {{ $t('新建部署') }} {{ isLesscodeApp ? $t('版本') : $t('分支') }}
              </div>
            </bk-select>
            <bk-button
              :theme="'primary'"
              class="ml10 mr15 vm"
              style="min-width: 120px"
              :loading="isDeploying"
              :disabled="deployDisabled"
              @click="handleDeploy"
            >
              <span>{{ `${$t('部署至')}${envName}` }}</span>
            </bk-button>
            <!-- <a class="vm" href="javascript: void(0);" @click="handleShowCommits" v-if="canShowCommits"> {{ $t('查看代码版本差异') }} </a> -->
            <div
              v-if="canShowCommits || (deploymentInfo && !isAppOffline)"
              class="operate"
            >
              <bk-dropdown-menu
                ref="dropdown"
                font-size="medium"
                @show="dropdownShow"
                @hide="dropdownHide"
              >
                <div
                  slot="dropdown-trigger"
                  class="dropdown-trigger-btn-branch"
                  style="padding-left: 19px"
                >
                  <span>{{ $t('更多操作') }}</span>
                  <i :class="['bk-icon icon-angle-down', { 'icon-flip': isDropdownShow }]" />
                </div>
                <ul
                  slot="dropdown-content"
                  class="bk-dropdown-list"
                >
                  <li v-if="canShowCommits">
                    <a
                      href="javascript: void(0);"
                      @click="handleShowCommits"
                    >
                      {{ $t('查看代码版本差异') }}
                    </a>
                  </li>
                  <li v-if="!isAppOffline">
                    <a
                      href="javascript:;"
                      @click="handleOfflineApp"
                    >
                      {{ $t('下架') }}
                    </a>
                  </li>
                </ul>
              </bk-dropdown-menu>
            </div>
          </div>

          <div
            v-if="environment === 'prod' && platformFeature.DEVELOPMENT_TIME_RECORD"
            class="paas-cost-box mt15"
          >
            <bk-checkbox
              v-model="costConf.enable"
              class="vm"
              :true-value="true"
              :false-value="false"
            >
              {{ $t('记录开发成本：开发本次发布内容耗时') }}
            </bk-checkbox>
            <bk-input
              v-model="costConf.hour"
              :clearable="false"
              :show-controls="false"
              type="number"
              :min="0"
              :precision="0"
              placeholder=" "
              style="display: inline-block; width: 50px"
            />
            <span>{{ $t('时') }}</span>
            <bk-input
              v-model="costConf.minute"
              :clearable="false"
              :show-controls="false"
              type="number"
              :max="59"
              :min="0"
              :precision="0"
              placeholder=" "
              style="display: inline-block; width: 50px"
            />
            <span>{{ $t('分') }}</span>
          </div>
        </div>

        <div v-else>
          <strong class="f14 mb10">{{ $t('部署前需完成以下准备工作') }}</strong>
          <div class="preparation-list">
            <div
              v-for="item of deployPreparations.failed_conditions"
              :key="item.action_name"
              class="preparation-item"
            >
              <span class="paasng-icon paasng-exclamation-triangle-shape" />
              <p
                v-bk-overflow-tips
                class="desc"
              >
                {{ item.message }}
              </p>
              <a
                v-if="item.action_name !== 'CHECK_ENV_PROTECTION'"
                href="javascript: void(0);"
                class="action"
                @click="handleFixPreparation(item)"
              >
                {{ $t('立即处理') }}
              </a>
            </div>
          </div>
        </div>

        <p
          class="error-tip"
          v-if="isShowSelectTip"
        >
          {{ branchEmptyText }}
        </p>
      </div>
    </template>

    <div
      class="deploy-view"
      :style="{ 'margin-top': `${isScrollFixed ? '104px' : '0'}` }"
    >
      <div
        id="deploy-timeline-box"
        style="width: 230px"
      >
        <deploy-timeline
          ref="deployTimelineRef"
          :key="timelineComKey"
          :list="timeLineList"
          :stage="curDeployStage"
          :disabled="isWatchDeploying || isDeploySuccess || isDeployFail || isDeployInterrupted || isDeployInterrupting"
          @select="handleTimelineSelect"
        />
      </div>
      <deploy-log
        v-if="isWatchDeploying || isDeploySuccess || isDeployFail || isDeployInterrupted || isDeployInterrupting"
        ref="deployLogRef"
        :build-list="streamLogs"
        :ready-list="readyLogs"
        :process-list="allProcesses"
        :state-process="appearDeployState"
        :process-loading="processLoading"
        :environment="environment"
      />
      <div
        v-else-if="curTimeline"
        class="pre-deploy-detail"
      >
        <div
          v-for="metadata of curTimeline.displayBlocks"
          :key="metadata.key"
          class="metadata-card"
        >
          <strong class="card-title">
            {{ metadata.name }}
            <router-link
              v-if="metadata.routerName"
              v-bk-tooltips="metadata.name === $t('访问地址') ? $t('查看') : $t('配置')"
              class="card-edit"
              :to="{ name: metadata.routerName, params: { id: appCode, moduleId: curModuleId } }"
            >
              <span
                v-if="metadata.name === $t('访问地址')"
                class="paasng-icon paasng-chain"
              />
              <!-- lesscode 应用 和 smart 应用不展示这个 配置按钮 -->
              <template v-else>
                <span
                  v-if="isShowConfig"
                  class="paasng-icon paasng-cog"
                />
              </template>
            </router-link>
          </strong>
          <ul class="card-list">
            <li
              v-for="(item, index) of metadata.infos"
              :key="index"
              class="card-item"
            >
              <template v-if="metadata && metadata.type === 'key-value'">
                <div class="card-key">{{ item.text }}：</div>
                <template v-if="Array.isArray(item.value)">
                  <div
                    v-if="item.value.length"
                    class="card-value"
                  >
                    <template v-if="isSmartApp && item.text === $t('源码管理')">
                      {{ $t('蓝鲸 S-mart 源码包') }}
                    </template>
                    <span
                      v-for="(subItem, subIndex) of item.value"
                      :key="subIndex"
                      class="card-value-item mr5"
                    >
                      <router-link :to="subItem.route">
                        {{ subItem.name }}
                      </router-link>
                    </span>
                  </div>
                  <div
                    v-else
                    class="card-value"
                  >
                    {{ $t('无') }}
                  </div>
                </template>
                <template v-else>
                  <div class="card-value">
                    <template v-if="item.text === $t('地址')">
                      <template v-if="item.value">
                        <span v-if="curAppModule.source_origin === GLOBAL.APP_TYPES.IMAGE">{{ item.value }}</span>
                        <a
                          v-else
                          :href="item.value"
                          target="_blank"
                        >
                          {{ item.value }}
                        </a>
                      </template>
                      <span v-else>{{ $t('无') }}</span>
                    </template>
                    <template v-else>
                      {{ item.value || $t('无') }}
                    </template>
                    <span v-if="item.value && item.href">
                      <a
                        target="_blank"
                        :href="item.href"
                        style="color: #3a84ff"
                      >
                        {{ item.hrefText }}
                      </a>
                    </span>
                    <a
                      v-if="!curAppModule.repo.linked_to_internal_svn && item.downloadBtn"
                      class="ml5"
                      href="javascript: void(0);"
                      @click="item.downloadBtn"
                    >
                      {{ item.downloadBtnText }}
                    </a>
                    <!-- <a :href="item.value" target="_blank" v-if="item.text === $t('地址')"> {{ $t('点击访问') }} </a> -->
                    <a
                      v-if="
                        item.text === $t('源码管理') &&
                        lessCodeFlag &&
                        curAppModule.source_origin === GLOBAL.APP_TYPES.LESSCODE_APP
                      "
                      :target="lessCodeData.address_in_lesscode ? '_blank' : ''"
                      :href="lessCodeData.address_in_lesscode || 'javascript:;'"
                      @click="handleLessCode"
                    >
                      {{ $t('我要开发') }}
                    </a>
                  </div>
                </template>
              </template>
              <template v-else>
                <a
                  :href="item.value"
                  target="_blank"
                >
                  {{ $t(item.text) }}
                </a>
              </template>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <bk-dialog
      v-model="commitDialog.visiable"
      width="740"
      :title="$t('查看版本差异')"
      :theme="'primary'"
      :mask-close="true"
      :show-footer="false"
    >
      <div class="result">
        <paas-loading :loading="commitDialog.isLoading">
          <div
            v-if="!commitDialog.isLoading"
            slot="loadingContent"
          >
            <form
              v-if="deploymentInfo"
              class="ps-form ps-form-horizontal"
            >
              <div class="middle-list mb15">
                <span class="">
                  {{ $t('已选中分支：') }}
                  <strong>{{ branchSelection.split(':')[1] || '--' }}</strong>
                </span>
                <span class="revision-diff-sep ml25 mr25">&lt; &gt;</span>
                <span class="">
                  {{ $t('已部署分支：') }}
                  <strong>
                    {{ deploymentInfo.repo.name }}
                    （{{ $t('版本号') }}: {{ deploymentInfo.repo.version }} ）
                  </strong>
                </span>
              </div>
            </form>
            <table class="ps-table ps-table-default ps-table-outline">
              <colgroup>
                <col style="width: 150px" />
                <col style="width: 150px" />
                <col style="width: 170px" />
                <col style="width: 250px" />
              </colgroup>
              <tr class="ps-table-environment-header">
                <th>{{ $t('版本号') }}</th>
                <th>{{ $t('提交人') }}</th>
                <th>{{ $t('提交时间') }}</th>
                <th>{{ $t('注释') }}</th>
              </tr>
              <tr
                v-if="!commitsList.length"
                class="ps-table-slide-up"
              >
                <td colspan="4">
                  <div class="ps-no-result">
                    <div class="text">
                      <p><i class="paasng-icon paasng-empty no-data" /></p>
                      <p>{{ $t('暂无版本差异记录') }}</p>
                    </div>
                  </div>
                </td>
              </tr>
              <tbody
                v-for="(cItem, index) in commitsList"
                v-else
                :key="index"
                :class="['ps-table-template', { open: commitDialog.curCommitsIndex === index }]"
              >
                <tr
                  class="ps-table-slide-up"
                  @click.stop.prevent="handleToggleCommitsDetail(index)"
                >
                  <td class="pl50">
                    <i class="icon" />
                    <a>{{ cItem.revision }}</a>
                  </td>
                  <td>{{ cItem.author }}</td>
                  <td>{{ cItem.date }}</td>
                  <td>{{ cItem.message }}</td>
                </tr>
                <tr class="ps-table-slide-down">
                  <td colspan="4">
                    <pre>
                      <p
                        v-for="(chagnItem, chagnItemIndex) in cItem.changelist"
                        :key="chagnItemIndex"
                      >{{ chagnItem[0] }} {{ chagnItem[1] }}</p>
                    </pre>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </paas-loading>
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="offlineAppDialog.visiable"
      ext-cls="remove-module-dialog-cls"
      width="450"
      :title="`${$t('下架模块')}${curAppModule.name}${environment === 'stag' ? $t('预发布环境') : $t('生产环境')}`"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      :loading="offlineAppDialog.isLoading"
      @confirm="confirmOfflineApp"
      @cancel="cancelOfflineApp"
    >
      <div class="tl">
        {{ $t('模块下架，会停止当前模块下所有进程，增强服务等模块的资源仍然保留，确认下架？') }}
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="confirmDeployConf.visiable"
      width="480"
      :title="confirmDeployConf.title"
      :theme="'primary'"
      :mask-close="false"
      :draggable="false"
      header-position="left"
      :show-footer="!schemaIsLoading"
      @confirm="createDeploy"
      @cancel="handleCancelDeploy"
    >
      <template slot="footer">
        <bk-button
          v-if="confirmDeployConf.architecture !== 'arm64'"
          :theme="'primary'"
          :title="$t('主要按钮')"
          class="mr10"
          @click="createDeploy"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          :theme="'default'"
          type="submit"
          :title="$t('基础按钮')"
          class="mr10"
          @click="handleCancelDeploy"
        >
          {{ $t('取消') }}
        </bk-button>
      </template>
      <bk-container
        :col="12"
        :margin="0"
      >
        <bk-row
          v-if="!isLesscodeApp && curAppModule.source_origin === GLOBAL.APP_TYPES.IMAGE"
          class="mb15"
        >
          <bk-col
            class="pr0 f14"
            :span="3"
          >
            <span class="confirm-key">{{ $t('镜像标签：') }}</span>
          </bk-col>
          <bk-col
            class="pl0 f14"
            :span="9"
          >
            <span class="confirm-value">{{ confirmDeployConf.branchName }}</span>
          </bk-col>
        </bk-row>
        <bk-row
          v-if="curAppModule.source_origin !== GLOBAL.APP_TYPES.IMAGE"
          class="mb15"
        >
          <bk-col
            class="pr0 f14"
            :span="3"
          >
            <span class="confirm-key">{{ $t('分支名称：') }}</span>
          </bk-col>
          <bk-col
            class="pl0 f14"
            :span="9"
          >
            <span class="confirm-value">{{ confirmDeployConf.branchName }}</span>
          </bk-col>
        </bk-row>
        <bk-row
          v-if="curAppModule.source_origin !== GLOBAL.APP_TYPES.IMAGE"
          class="mb15"
        >
          <bk-col
            class="pr0 f14"
            :span="3"
          >
            <span class="confirm-key">{{ $t('版本：') }}</span>
          </bk-col>
          <bk-col
            class="pl0 f14"
            :span="9"
          >
            <span class="confirm-value">{{ confirmDeployConf.version }}</span>
          </bk-col>
        </bk-row>
        <template v-if="curAppModule.source_origin !== GLOBAL.APP_TYPES.IMAGE">
          <bk-row
            v-if="confirmDeployConf.updateTime"
            class="mb15"
          >
            <bk-col
              class="pr0 f14"
              :span="3"
            >
              <span class="confirm-key">{{ $t('最近更新时间：') }}</span>
            </bk-col>
            <bk-col
              class="pl0 f14"
              :span="9"
            >
              <span class="confirm-value">{{ changeTime(confirmDeployConf.updateTime) }}</span>
            </bk-col>
          </bk-row>
          <bk-row
            v-if="confirmDeployConf.message"
            class="mb15"
          >
            <bk-col
              class="pr0 f14"
              :span="3"
            >
              <span class="confirm-key">{{ $t('版本描述：') }}</span>
            </bk-col>
            <bk-col
              class="pl0 f14"
              :span="9"
            >
              <pre class="confirm-value desc">{{ confirmDeployConf.message }}</pre>
            </bk-col>
          </bk-row>
          <template v-if="branchInfoType === 'image'">
            <bk-row class="mb15">
              <bk-col
                class="pr0 f14"
                :span="10"
              >
                <bk-checkbox
                  v-model="imagePullPolicy"
                  :true-value="'Always'"
                  :false-value="'IfNotPresent'"
                >
                  {{ $t('总在创建进程实例前拉取镜像') }}
                </bk-checkbox>
              </bk-col>
              <bk-col
                class="pr0 f14"
                :span="12"
              >
                <p class="mirrorInfo">
                  {{ $t('每个镜像版本默认仅拉取一次，如版本内容有更新，请勾选该项') }}
                </p>
              </bk-col>
            </bk-row>
          </template>
        </template>
        <template v-else>
          <paas-content-loader
            :is-loading="schemaIsLoading"
            placeholder="index-loading"
            :offset-top="0"
            :height="140"
            class="app-container middle framework-wrapper"
          >
            <bk-row class="mb15">
              <bk-col
                class="pr0 f14"
                :span="3"
              >
                <span class="confirm-key">{{ $t('镜像架构：') }}</span>
              </bk-col>
              <bk-col
                class="pl0 f14"
                :span="9"
              >
                <span class="confirm-value">{{ confirmDeployConf.architecture || '--' }}</span>
              </bk-col>
            </bk-row>
            <bk-row class="mb15">
              <bk-col
                class="pr0 f14"
                :span="3"
              >
                <span class="confirm-key">{{ $t('最近更新时间：') }}</span>
              </bk-col>
              <bk-col
                class="pl0 f14"
                :span="9"
              >
                <span class="confirm-value">{{ changeTime(confirmDeployConf.lastUpdate) || '--' }}</span>
              </bk-col>
            </bk-row>
            <bk-row
              v-if="confirmDeployConf.architecture === 'amd64'"
              class="mb15"
            >
              <bk-col
                class="pr0 f14"
                :span="10"
              >
                <bk-checkbox
                  v-model="imagePullPolicy"
                  :true-value="'Always'"
                  :false-value="'IfNotPresent'"
                >
                  {{ $t('总在创建进程实例前拉取镜像') }}
                </bk-checkbox>
              </bk-col>
              <bk-col
                class="pr0 f14"
                :span="12"
              >
                <p class="mirrorInfo">
                  {{ $t('每个镜像标签（Tag）默认仅拉取一次，如旧标签内容有更新，请勾选该项') }}
                </p>
              </bk-col>
            </bk-row>
            <bk-row
              v-else
              class="mb15"
            >
              <template v-if="confirmDeployConf.architecture">
                <bk-col
                  class="pr0 f14"
                  :span="12"
                >
                  <div :class="['ps-tip-block', 'error-wrapper', 'is-danger']">
                    <p>
                      {{ $t('当前不支持') }} {{ confirmDeployConf.architecture }} {{ $t('架构的镜像部署，请参考') }}
                      <a
                        :href="GLOBAL.DOC.ARCHITECTURE_PLATFORM_IMAGE"
                        target="_blank"
                        class="doc-style"
                      >
                        {{ $t('文档重新构建镜像') }}
                      </a>
                    </p>
                  </div>
                </bk-col>
              </template>
            </bk-row>
          </paas-content-loader>
        </template>
      </bk-container>
    </bk-dialog>

    <bk-dialog
      v-model="stopDeployConf.visiable"
      width="480"
      :title="stopDeployConf.title"
      :theme="'primary'"
      :mask-close="false"
      :draggable="false"
      header-position="left"
      @confirm="confirmStopDeploy"
      @cancel="cancelStopDeploy"
      @after-leave="afterLeaveStopDeploy"
    >
      <div v-if="stopDeployConf.stage === 'build'">
        {{ $t('数据库如有变更操作') }}，
        <span style="color: #f00">
          {{ $t('数据库变更可能会异常中断且无法回滚') }}
        </span>
        ，{{ $t('请留意表结构') }}。
      </div>
      <div v-else>
        {{ $t('部署命令已经下发') }}，
        <span style="color: #f00">{{ $t('仅停止检查部署结果') }}</span>
        ，{{ $t('请留意进程状态') }}。
      </div>
    </bk-dialog>
  </paas-content-loader>
</template>

<script>
import moment from 'moment';
import appBaseMixin from '@/mixins/app-base-mixin.js';
import deployTimeline from '../deploy-timeline';
import deployLog from '../deploy-log';
import { bus } from '@/common/bus';
import { fileDownload } from '@/common/utils';

export default {
  isBranchesLoading: true,
  components: {
    deployTimeline,
    deployLog,
  },
  mixins: [appBaseMixin],
  props: {
    environment: {
      type: String,
      default: 'stag',
    },
  },
  data() {
    const curDeployResult = {
      possible_reason: '',
      logs: '',
      exposedLink: '',
      title: '',
      result: '',
      resultMessage: this.$t('应用部署成功，已发布至蓝鲸应用市场。'),
      error_tips: null,
      getResultDisplay() {
        if (this.result === 'successful') {
          return this.$t('部署成功');
        }
        return this.$t('部署失败');
      },
      getTitleDisplay() {
        if (this.result) {
          return this.$t('项目部署结束');
        }
        return this.title;
      },
    };

    return {
      isLoading: true,
      deployTotalTime: 0,
      startDeployTime: 0,
      totalTimer: 0,
      offlineTimer: 0,
      isScrollFixed: false,
      branchSelection: '',
      timeLineList: [],
      offlineAppDialog: {
        visiable: false,
        isLoading: false,
      },
      confirmDeployConf: {
        title: '',
        branchName: '',
        version: '',
        message: '',
        updateTime: '',
        visiable: false,
        isLoading: false,
        architecture: '',
        lastUpdate: '',
      },
      costConf: {
        enable: false,
        hour: '',
        minute: '',
      },
      isAppOffline: false,
      isWatchOfflineing: false,
      overview: {
        repo: {
          source_type: '',
          type: '',
          trunk_url: '',
          repo_url: '',
          repo_fullname: '',
          use_external_diff_page: true,
          linked_to_internal_svn: false,
          display_name: '',
        },
        stack: '',
        image: '',
        buildpacks: [],
      },
      commitDialog: {
        visiable: false,
        isLoading: false,
        curCommitsIndex: -1,
      },
      commitsList: [],
      isDeploying: false,
      isWatchDeploying: false,
      isLogError: false,
      deploymentInfo: null,
      lastDeploymentInfo: null,
      curDeployResult,
      ansiUp: null,
      exposedLink: '',
      branchesMap: {},
      branchList: [],
      streamLogs: [],
      deployPreparations: {
        all_conditions_matched: true,
        failed_conditions: [],
      },
      curDeployId: '',
      eventSourceState: {
        CLOSED: 2,
      },
      watchTimer: 0,
      reConnectLimit: 5,
      reConnectTimes: 0,
      timeoutDebounced: null,
      isDeploySuccess: false,
      isDeployFail: false,
      isDeployInterrupted: false,
      isDeployInterrupting: false,
      curTimeline: {
        displayBlocks: [
          {
            name: this.$t('帮助文档'),
            type: 'link',
            key: 'default',
            infos: [
              {
                text: this.$t('示例：如何为 Python 应用添加 celery 后台任务进程'),
                value: this.GLOBAL.DOC.PROCESS_CELERY,
              },
              {
                text: this.$t('应用进程概念介绍以及如何使用'),
                value: this.GLOBAL.DOC.PROCESS_INTRO,
              },
              {
                text: this.$t('应用内部进程通信指南'),
                value: this.GLOBAL.DOC.PROCESS_IPC,
              },
            ],
          },
        ],
      },
      isFirstDeploy: false,
      cost: {
        hour: 0,
        minute: 0,
      },

      prevProcessVersion: 0,
      prevInstanceVersion: 0,
      summaryOffsetLeft: 270,
      summaryOffsetTop: 300,
      summaryWidth: 900,
      timelineOffsetLeft: 270,
      timelineWidth: 230,
      allProcesses: [],
      readyLogs: [],
      appearDeployState: [],
      processLoading: false,
      serverProcessEvent: null,
      serverLogEvent: null,
      serverTimeout: 30,
      deployStartTimeQueue: [],
      deployEndTimeQueue: [],
      appMarketPublished: false,
      timelineComKey: -1,

      stopDeployConf: {
        title: '',
        visiable: false,
        isLoading: false,
        stage: '',
      },
      deploymentId: '',
      initLanguage: '',
      initTemplateType: '',
      initTemplateDesc: '',
      isDropdownShow: false,
      imagePullPolicy: 'IfNotPresent',
      schemaIsLoading: true,
      branchInfoType: '',
      lessCodeData: {},
      lessCodeFlag: true,
      serverEventErrorTimer: 0,
      serverEventEOFTimer: 0,
    };
  },
  computed: {
    buildpacks() {
      if (this.overview.buildpacks && this.overview.buildpacks.length) {
        const buildpacks = this.overview.buildpacks.map((item) => item.display_name);
        return buildpacks.join('，');
      }
      return '--';
    },
    isNotDeployForStag() {
      return this.environment === 'prod' && this.branchSelection !== this.availableBranch;
    },
    availableBranch() {
      if (this.$store.state.deploy.availableBranch) {
        return `${this.$store.state.deploy.availableType}:${this.$store.state.deploy.availableBranch}`;
      }
      return '';
    },
    canShowCommits() {
      return !this.isLesscodeApp && !!this.deploymentInfo && this.overview?.repo?.diff_feature?.enabled;
    },
    envName() {
      return this.environment === 'stag' ? this.$t('预发布环境') : this.$t('生产环境');
    },
    deployDisabled() {
      // 没有分支列表
      if (this.branchList.length === 0) {
        return true;
      }

      // 未开启授权
      // if (!this.isAuthFlag && this.isShowTips) {
      //     return true
      // }

      return false;
    },
    curDeployStage() {
      const flag =
        this.isWatchDeploying ||
        this.isDeploySuccess ||
        this.isDeployFail ||
        this.isDeployInterrupted ||
        this.isDeployInterrupting;
      return flag ? 'deploy' : 'noDeploy';
    },
    deployTotalTimeDisplay() {
      return this.getDisplayTime(this.deployTotalTime);
    },
    scrollStyle() {
      if (this.isScrollFixed) {
        return {
          summary: {
            position: 'fixed',
            left: `${this.summaryOffsetLeft}px`,
            width: `${this.summaryWidth}px`,
            top: '40px',
            background: '#FFF',
            'z-index': 100,
          },
          timeline: {
            position: 'fixed',
            left: `${this.summaryOffsetLeft + 30}px`,
            width: `${this.timelineWidth}px`,
            top: '110px',
            background: '#FFF',
            'z-index': 100,
          },
        };
      }
      return {
        summary: {},
        timeline: {},
      };
    },

    branchEmptyText() {
      const sourceType = this.overview.repo && this.overview.repo.source_type;
      if (['bare_svn', 'bare_git'].includes(sourceType)) {
        if (this.branchList.length === 0) {
          return sourceType === 'bare_svn' ? this.$t('请检查SVN账号是否正确') : this.$t('请检查Git账号是否正确');
        }
        return this.$t('暂无选项');
      }
      return this.$t('暂无选项');
    },
    platformFeature() {
      return this.$store.state.platformFeature;
    },
    initTemplateTypeDisplay() {
      // 初始化模板类型
      return `${this.initTemplateType}(${this.initLanguage})`;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    isSmartApp() {
      return this.curAppModule.source_origin === this.GLOBAL.APP_TYPES.SMART_APP;
    },
    isShowConfig() {
      let flag = true;
      if (this.isSmartApp) {
        flag = false;
      }
      if (this.curAppModule.source_origin === this.GLOBAL.APP_TYPES.LESSCODE_APP) {
        flag = false;
      }
      return flag;
    },
    isShowSelectTip() {
      return this.branchEmptyText !== this.$t('暂无选项');
    },
  },
  watch: {
    isWatchDeploying() {
      this.$nextTick(() => {
        this.computedBoxFixed();
        this.stopDeployConf.visiable = false;
      });
    },
    isWatchOfflineing() {
      this.$nextTick(() => {
        this.computedBoxFixed();
      });
    },

    isDeploySuccess() {
      this.$nextTick(() => {
        this.computedBoxFixed();
      });
    },

    isDeployFail() {
      this.$nextTick(() => {
        this.computedBoxFixed();
      });
    },

    isDeployInterrupted() {
      this.$nextTick(() => {
        this.computedBoxFixed();
      });
    },

    isDeployInterrupting() {
      this.$nextTick(() => {
        this.computedBoxFixed();
      });
    },

    lastDeploymentInfo() {
      if (this.lastDeploymentInfo && this.lastDeploymentInfo.repo) {
        this.$nextTick(() => {
          this.branchSelection = `${this.lastDeploymentInfo.repo.type}:${this.lastDeploymentInfo.repo.name}`;
        });
      }
    },
  },
  created() {
    // moment日期中英文显示
    moment.locale(this.localLanguage);
    // 部署处于准备阶段的判断标识，用于获取准备阶段的日志
    this.isDeployReady = true;
    // 部署阶段时轮询查procee定时器
    this.fetchProcessTimer = null;
    this.isDeploySseEof = true;
    this.releaseId = '';
    this.init();
  },
  mounted() {
    // 初始化日志彩色组件
    // eslint-disable-next-line
    const AU = require('ansi_up');
    // eslint-disable-next-line
    this.ansiUp = new AU.default();

    window.addEventListener('scroll', () => {
      this.isScrollFixed =
        (this.isWatchDeploying ||
          this.isWatchOfflineing ||
          this.isDeploySuccess ||
          this.isDeployFail ||
          this.isDeployInterrupted ||
          this.isDeployInterrupting) &&
        window.pageYOffset >= 260;
    });

    window.addEventListener('resize', () => {
      this.computedBoxFixed();
    });
  },
  beforeDestroy() {
    // 关闭连接，防止TCP过多(chrome一个域名最多6个)，导致后续请求pending
    this.serverLogEvent && this.serverLogEvent.close();
    this.serverProcessEvent && this.serverProcessEvent.close();
    window.onscroll = null;
    this.clearPrevDeployData();
  },
  methods: {
    async init() {
      this.getModuleRuntimeOverview();
      this.getDeployPreparations();
      this.getModuleReleaseInfo();
      this.getModuleBranches();
      this.checkOfflineOperation();
      this.getAppDocLinks();
      this.getLastDeployHistory();
      // this.refreshAvailableBranch()

      // 先获取各个阶段数据，防止状态丢失
      await this.fetchModuleInfo(); // 获取模块信息
      await this.fetchLanguageInfo(); // 获取模版说明
      await this.getLessCode(); // 获取开发信息
      this.getPreDeployDetail();
      this.checkDeployOperation();
    },
    clearPrevDeployData() {
      this.branchList = [];
      this.commitsList = [];
      this.branchSelection = '';
      this.appMarketPublished = false;
      this.handleClearDeploy();
      clearTimeout(this.timer);
      clearInterval(this.offlineTimer);
    },

    async getModuleRuntimeOverview() {
      try {
        const res = await this.$store.dispatch('deploy/getModuleRuntimeOverview', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.overview = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    async refreshAvailableBranch() {
      try {
        await this.$store.dispatch('deploy/refreshAvailableBranch', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    computedBoxFixed() {
      const box = document.querySelector('.deploy-action-box');
      // const box = document.getElementById('deploying-box') || document.getElementById('offlineing-box') || document.getElementById('success-box') || document.getElementById('fail-box')
      if (box && box.getBoundingClientRect) {
        const elementRect = box?.getBoundingClientRect();
        this.summaryOffsetLeft = elementRect.x;
        this.summaryOffsetTop = elementRect.y;
        this.summaryWidth = elementRect.width;
      }
    },

    handleResetData() {
      this.readyLogs = [];
      this.streamLogs = [];
      this.allProcesses = [];
    },

    async getDeployPreparations() {
      try {
        const res = await this.$store.dispatch('deploy/getDeployPreparations', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
        });
        this.deployPreparations = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    async getModuleBranches(favBranchName) {
      this.isBranchesLoading = true;
      try {
        // 获取上次部署staging环境的分支
        const availableBranch = await this.$store.dispatch('deploy/refreshAvailableBranch', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        const res = await this.$store.dispatch('deploy/getModuleBranches', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });

        //  Smart 应用(预发布/生产)显示最新分支
        if (this.isSmartApp) {
          const sortList = res.results.sort(this.sortData);
          this.branchSelection = `${sortList[0].type}:${sortList[0].name}`;
        }
        const branchesData = res.results;
        const branchesList = [];
        branchesData.forEach((branch, index) => {
          const branchId = `${branch.type}:${branch.name}`;
          let branchName = branch.name;

          if (this.environment === 'prod' && branchId === availableBranch) {
            branchName = `${branch.name}${this.$t('（已在预发布环境成功部署）')}`;
          }

          const obj = {
            id: branchId,
            text: branchName,
            type: branch.type,
          };

          // 组装数据，实现分组
          if (!branchesList.map((item) => item.id).includes(branch.type)) {
            branchesList.push({
              id: branch.type,
              name: branch.type,
              displayName: branch.display_type,
              children: [obj],
            });
          } else {
            const curData = branchesList.find((item) => item.id === branch.type);
            curData.children.push(obj);
          }

          this.branchesMap[branchId] = branch;
        });
        this.branchList = branchesList;
        this.initBranchSelection(favBranchName);
      } catch (e) {
        this.branchList = [];
        if (!e.code === 'APP_NOT_RELEASED') {
          this.$paasMessage({
            theme: 'error',
            message: e.detail || e.message || this.$t('接口异常'),
          });
        }
      } finally {
        this.isBranchesLoading = false;
      }
    },

    sortData(a, b) {
      return new Date(b.last_update).getTime() - new Date(a.last_update).getTime();
    },

    initBranchSelection(favBranchName) {
      // 如果是刚刚创建新分支，默认选中新建的分支
      // 如果相应环境上次部署过，默认选中上次部署的分支
      // 如果正式环境没有部署过，默认选中预发布环境部署过的分支

      if (favBranchName && this.branchesMap.hasOwnProperty(favBranchName)) {
        this.branchSelection = favBranchName;
        return;
      }

      if (this.branchList.length && !this.branchSelection) {
        if (this.environment === 'prod') {
          if (this.availableBranch) {
            this.branchSelection = this.availableBranch;
          } else {
            this.branchSelection = this.branchList[0].children[0].id;
          }
        } else {
          // 默认选中第一个
          this.branchSelection = this.branchList[0].children[0].id;
        }
      }
    },

    handleTimelineSelect(timelineData) {
      this.curTimeline = timelineData;

      if (this.appearDeployState.includes(timelineData.stage)) {
        this.$refs.deployLogRef && this.$refs.deployLogRef.handleScrollToLocation(timelineData.stage);
      }
    },

    async getModuleReleaseInfo() {
      try {
        const res = await this.$store.dispatch('deploy/getModuleReleaseInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
        });
        if (!res.code) {
          // 已下架
          if (res.is_offlined) {
            res.offline.repo.version = this.formatRevision(res.offline.repo.revision);
            this.deploymentInfo = res.offline;
            this.exposedLink = '';
            this.isAppOffline = true;
          } else if (res.deployment) {
            res.deployment.repo.version = this.formatRevision(res.deployment.repo.revision);
            this.deploymentInfo = res.deployment;
            this.exposedLink = res.exposed_link.url;
            this.isAppOffline = false;
          } else {
            this.deploymentInfo = {
              repo: {},
            };
          }

          // 是否第一次部署
          this.isFirstDeploy = !res.deployment;
        } else {
          this.isFirstDeploy = true;
        }
      } catch (e) {
        this.deploymentInfo = null;
        this.isFirstDeploy = true;
        this.exposedLink = '';
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    handleToggleCommitsDetail(index) {
      if (this.commitDialog.curCommitsIndex === index) {
        this.commitDialog.curCommitsIndex = -1;
      } else {
        this.commitDialog.curCommitsIndex = index;
      }
    },

    handleCancelDeploy() {
      this.confirmDeployConf.visiable = false;
    },

    /**
     * 准备部署模块
     */
    handleDeploy() {
      this.schemaIsLoading = true;
      this.getBranchInfoType();

      this.curAppModule.source_origin === this.GLOBAL.APP_TYPES.IMAGE
        ? this.getSchemaInfo()
        : (this.schemaIsLoading = false);

      if (this.deployDisabled) {
        return false;
      }

      if (!this.branchSelection) {
        this.$paasMessage({
          theme: 'error',
          message: this.isLesscodeApp ? this.$t('请选择部署版本') : this.$t('请选择部署分支'),
        });
        return false;
      }

      if (this.costConf.enable && this.environment === 'prod') {
        if (!this.costConf.hour && !this.costConf.minute) {
          this.$paasMessage({
            theme: 'error',
            message: this.$t('请填写开发成本'),
          });
          return false;
        }
      }

      this.confirmDeployConf.title =
        this.environment === 'stag' ? this.$t('确认部署预发布环境？') : this.$t('确认部署生产环境？');

      const branchInfo = this.branchesMap[this.branchSelection];

      if (!branchInfo) {
        this.$paasMessage({
          theme: 'error',
          message: this.isLesscodeApp ? this.$t('请选择部署版本') : this.$t('请选择部署分支'),
        });
        return false;
      }

      this.confirmDeployConf.branchName = branchInfo.name;
      this.confirmDeployConf.version = this.formatRevision(branchInfo.revision);
      this.confirmDeployConf.message = branchInfo.message || '';
      this.confirmDeployConf.updateTime = branchInfo.last_update || '';
      this.confirmDeployConf.visiable = true;
    },

    /**
     * 获取架构信息
     */
    async getSchemaInfo() {
      const branchInfo = this.branchesMap[this.branchSelection];
      try {
        const res = await this.$store.dispatch('deploy/getSchemaInfo', {
          appCode: this.appCode,
          moduleName: this.curModuleId,
          versionType: branchInfo.type,
          versionName: branchInfo.name,
        });
        this.confirmDeployConf.architecture = res.extra.architecture;
        this.confirmDeployConf.lastUpdate = res.last_update;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        this.schemaIsLoading = false;
      }
    },

    /**
     * 发起模块部署
     */
    async createDeploy() {
      const { isDeployFail } = this;

      // 处理状态
      this.isDeploying = true;
      this.isDeployReady = true;
      this.isDeployFail = false;
      this.isDeploySuccess = false;
      this.confirmDeployConf.visiable = false;

      this.appearDeployState = [];
      this.readyLogs = [];
      this.streamLogs = [];
      this.allProcesses = [];
      this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.handleResetStatus();

      const branchInfo = this.branchesMap[this.branchSelection];
      const params = {
        environment: this.environment,
        code: this.appCode,
        revision: branchInfo.revision,
        url: branchInfo.url,
        version_type: branchInfo.type,
        version_name: branchInfo.name,
        advanced_options: {
          image_pull_policy: this.imagePullPolicy,
        },
      };

      // 如果生产环境启用成本计算
      if (this.costConf.enable && this.environment === 'prod') {
        const hour = parseInt(this.costConf.hour || '0');
        const minute = parseInt(this.costConf.minute || '0');
        const devTime = hour + minute / 60;
        params.advanced_options.dev_hours_spent = devTime;
      }

      this.curDeployId = this.formatRevision(branchInfo.revision);

      // 上一次部署失败，点击重新部署触发的 createDeploy
      if (isDeployFail) {
        this.isWatchDeploying = true;
      }

      try {
        const res = await this.$store.dispatch('deploy/createDeployForModule', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          params,
        });
        this.reConnectTimes = 0;
        this.watchDeployStatus(res.deployment_id);
        this.deploymentId = res.deployment_id;

        this.isDeployInterrupted = false;
        this.isDeployInterrupting = false;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('部署失败，请稍候再试'),
        });
      } finally {
        this.isDeploying = false;
      }
    },

    computedTotalTime() {
      const startTime = new Date(this.deployStartTimeQueue[0]).getTime();
      const endTime = new Date(this.deployEndTimeQueue[this.deployEndTimeQueue.length - 1]).getTime();
      this.deployTotalTime = (endTime - startTime) / 1000;
    },

    getDisplayTime(payload) {
      let theTime = payload;
      if (theTime < 1) {
        return `< 1${this.$t('秒')}`;
      }
      let middle = 0;
      let hour = 0;

      if (theTime > 60) {
        middle = parseInt(theTime / 60, 10);
        theTime = parseInt(theTime % 60, 10);
        if (middle > 60) {
          hour = parseInt(middle / 60, 10);
          middle = parseInt(middle % 60, 10);
        }
      }

      let result = '';

      if (theTime > 0) {
        result = `${theTime}${this.$t('秒')}`;
      }
      if (middle > 0) {
        result = `${middle}${this.$t('分')}${result}`;
      }
      if (hour > 0) {
        result = `${hour}${this.$t('时')}${result}`;
      }

      return result;
    },

    /**
     * 计算部署进程间的所花时间
     */
    computedDeployTime(startTime, endTime) {
      const start = new Date(startTime).getTime();
      const end = new Date(endTime).getTime();
      const interval = (end - start) / 1000;

      if (!interval) {
        return `< 1${this.$t('秒')}`;
      }

      return this.getDisplayTime(interval);
    },

    /**
     * 监听部署进度，打印日志
     */
    watchDeployStatus(deployId) {
      this.serverLogEvent = null;
      this.timelineComKey = +new Date();
      this.streamLogs = [];
      this.streamPanelShowed = true;
      this.isWatchDeploying = true;
      this.isDeploySseEof = false;

      clearInterval(this.watchTimer);
      if (this.serverLogEvent === null || this.serverLogEvent.readyState === this.eventSourceState.CLOSED) {
        this.serverLogEvent = new EventSource(`${BACKEND_URL}/streams/${deployId}`, {
          withCredentials: true,
        });
        this.serverLogEvent.onmessage = (event) => {
          // 如果是error，会重新发起日志请求，在下次信息返回前清空上次信息
          if (this.isLogError) {
            this.streamLogs = [];
            this.isLogError = false;
            // streamLogItems = []
          }
          const item = JSON.parse(event.data);
          if (this.isDeployReady) {
            this.appearDeployState.push('preparation');
            this.$nextTick(() => {
              this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.editNodeStatus('preparation', 'pending', '');
            });
            this.readyLogs.push(this.ansiUp.ansi_to_html(item.line));
          } else {
            this.streamLogs.push(this.ansiUp.ansi_to_html(item.line));
          }
        };

        this.serverLogEvent.addEventListener('phase', (event) => {
          const item = JSON.parse(event.data);
          if (item.name === 'build') {
            this.isDeployReady = false;
          }

          if (['build', 'preparation'].includes(item.name)) {
            this.appearDeployState.push(item.name);
          }
          let content = '';
          if (item.status === 'successful') {
            this.deployStartTimeQueue.push(item.start_time);
            this.deployEndTimeQueue.push(item.complete_time);
          }

          if (item.name === 'release' && ['failed', 'successful'].includes(item.status)) {
            content = this.computedDeployTime(item.start_time, item.complete_time);
          }

          if (item.name === 'release' && item.status === 'successful') {
            // 部署成功
            this.isDeploySuccess = true;
            this.isWatchDeploying = false;
            this.getModuleReleaseInfo();
          } else if (item.status === 'failed') {
            // 部署失败
            this.isDeployFail = true;
            this.isWatchDeploying = false;
          } else if (item.status === 'interrupted') {
            // 停止部署成功
            this.isDeployInterrupted = true;
            this.isWatchDeploying = false;
            this.isDeployInterrupting = false;
          }
          this.$nextTick(() => {
            this.$refs.deployTimelineRef &&
              this.$refs.deployTimelineRef.editNodeStatus(item.name, item.status, content);
          });
        });

        this.serverLogEvent.addEventListener('step', (event) => {
          const item = JSON.parse(event.data);
          let content = '';

          if (item.name === this.$t('检测部署结果') && item.status === 'pending') {
            this.appearDeployState.push('release');
            this.releaseId = item.release_id;
            this.getProcessList(item.release_id, true);
            this.$nextTick(() => {
              this.$refs.deployLogRef && this.$refs.deployLogRef.handleScrollToLocation('release');
            });
          }

          if (['failed', 'successful'].includes(item.status)) {
            content = this.computedDeployTime(item.start_time, item.complete_time);
          }

          if (item.status === 'successful' && item.name === this.$t('检测部署结果')) {
            this.closeServerPush();
          }
          this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.editNodeStatus(item.name, item.status, content);
          this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.$forceUpdate();
        });

        this.serverLogEvent.onerror = (event) => {
          this.isLogError = true;

          if (this.serverLogEvent.readyState === this.eventSourceState.CLOSED) {
            // 超过重试限制
            if (this.reConnectTimes >= this.reConnectLimit) {
              this.$paasMessage({
                theme: 'error',
                message: this.$t('日志输出流异常，建议您刷新页面重试!'),
              });
            }

            this.reConnectTimes += 1;
            // cancel debounced before we start new one
            // this.timeoutDebounced.cancel()
            setTimeout(() => {
              this.watchDeployStatus(deployId);
            }, 3000);
          }
        };

        // 监听到部署结束
        this.serverLogEvent.addEventListener(
          'EOF',
          (event) => {
            this.reConnectTimes = 0;
            this.serverLogEvent.close();
            this.closeServerPush();
            this.isDeploySseEof = true;
            // this.allProcesses = JSON.parse(JSON.stringify(this.allProcesses))

            // 判断是否在准备阶段就失败
            const isReadyFailed = this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.handleGetIsInit();

            isReadyFailed && this.$refs.deployTimelineRef.editNodeStatus('preparation', 'failed', '');

            this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.handleSetFailed();

            if (this.isDeploySuccess) {
              this.$refs.deployTimelineRef.editNodeStatus('preparation', 'successful', '');
            }
            this.getDeployResult(deployId);
            bus.$emit('update_entrance');
          },
          false
        );

        // 监听到部署slider title变化
        this.serverLogEvent.addEventListener(
          'title',
          (event) => {
            this.curDeployResult.title = event.data;
          },
          true
        );
      }
    },

    /**
     * 获取最近部署记录
     */
    async getLastDeployHistory() {
      this.isPageLoading = true;
      const pageParams = {
        limit: 1,
        offset: 0,
        environment: this.environment,
      };

      try {
        const res = await this.$store.dispatch('deploy/getDeployHistory', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          pageParams,
        });

        const operation = res.results[0];
        const reg = RegExp('^[a-z0-9]{40}$');
        if (operation && operation.operation_type === 'online') {
          operation.id = operation.deployment.deployment_id;

          operation.repo = operation.deployment.repo;
          operation.repo.version = operation.deployment.repo.revision;
          if (reg.test(operation.deployment.repo.revision)) {
            operation.repo.version = operation.deployment.repo.revision.substring(0, 8);
          }
          this.lastDeploymentInfo = Object.assign({}, operation);
        } else {
          this.lastDeploymentInfo = null;
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
        this.lastDeploymentInfo = null;
      }
    },

    /**
     * 获取部署结果
     */
    async getDeployResult(deployId) {
      try {
        const res = await this.$store.dispatch('deploy/getDeployResult', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          deployId,
        });
        this.curDeployResult.result = res.status;
        this.curDeployResult.logs = res.logs;
        this.deployInProgress = false;
        this.hasHistoryDeployment = true;
        if (res.status === 'successful') {
          this.computedTotalTime();
          this.curDeployResult.possible_reason = '';
          this.curDeployResult.error_tips = null;

          const appInfo = await this.$store.dispatch('getAppInfo', {
            appCode: this.appCode,
            moduleId: this.curModuleId,
          });
          this.appMarketPublished = appInfo.web_config.market_published;
        } else {
          this.curDeployResult.possible_reason = res.error_tips.possible_reason;
          this.curDeployResult.error_tips = res.error_tips;
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('部署失败，请稍候再试'),
        });
      } finally {
        this.isDeploying = false;
        this.isWatchDeploying = false;
      }
    },

    formatRevision(revision) {
      // 修改后端返回的 repo 数据，增加额外字段
      // 追加 version 字段
      // 为 Git 类型版本号取前 8 位
      const reg = RegExp('^[a-z0-9]{40}$');
      let version = '';
      if (reg.test(revision)) {
        version = revision.substring(0, 8);
      } else {
        version = revision;
      }
      return version;
    },

    handleBranchSelect(value, option) {},

    /**
     * 查看代码提交记录
     */
    async showCommits() {
      if (!this.branchSelection) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('请选择部署分支'),
        });
        return false;
      }
      this.commitDialog.visiable = true;
      this.commitDialog.isLoading = true;

      try {
        const fromVersion = this.deploymentInfo.repo.revision;
        const toVersion = this.branchSelection;

        // 根据用户选择的分支获取提交记录
        const res = await this.$store.dispatch('deploy/getSvnCommits', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          fromVersion,
          toVersion,
        });
        this.commitsList = res.results;
      } catch (e) {
        this.commitsList = [];
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        this.commitDialog.isLoading = false;
      }
    },

    /**
     * 查看代码对比
     */
    async showCompare() {
      if (!this.branchSelection) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('请选择部署分支'),
        });
        return false;
      }

      const fromVersion = this.deploymentInfo.repo.revision;
      const toVersion = this.branchSelection;
      const win = window.open();
      try {
        const res = await this.$store.dispatch('deploy/getGitCompareUrl', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          fromVersion,
          toVersion,
        });
        win.location.href = res.result;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    /**
     * 查看代码差异
     */
    async handleShowCommits() {
      if (this.curAppModule.repo.diff_feature.method === 'external') {
        this.showCompare();
      } else {
        this.showCommits();
      }
    },

    /**
     * 处理部署前准备工作项
     */
    handleFixPreparation(preparation) {
      switch (preparation.action_name) {
        // 代码仓库没有授权
        case 'NEED_TO_BIND_OAUTH_INFO':
          this.$router.push({
            name: 'serviceCode',
          });
          break;

        // 没有访问源码仓库的权限
        case 'DONT_HAVE_ENOUGH_PERMISSIONS':
          this.$router.push({
            name: 'serviceCode',
          });
          break;

        // 蓝盾没有授权
        case 'CHECK_CI_GIT_TOKEN':
          this.$router.push({
            name: 'serviceCi',
          });
          break;

        // 完善市场信息
        case 'FILL_PRODUCT_INFO':
          this.$router.push({
            name: 'appMarket',
            params: {
              id: this.appCode,
            },
            query: {
              focus: 'baseInfo',
            },
          });
          break;

        // 自定义仓库源配置不正确
        case 'NEED_TO_CORRECT_REPO_INFO':
          this.$router.push({
            name: 'moduleManage',
            params: {
              id: this.appCode,
              moduleId: this.curModuleId,
            },
          });
          break;

        // 没有部署权限
        case 'CHECK_ENV_PROTECTION':
          this.$paasMessage({
            message: this.$t('请联系应用管理员'),
          });
          break;

        // 未完善进程启动命令
        case 'NEED_TO_COMPLETE_PROCFILE':
          this.$router.push({
            name: 'appDeployForConfig',
            query: {
              from: 'deployAction',
            },
          });
          break;

        // 未设置插件分类
        case 'FILL_PLUGIN_TAG_INFO':
          this.$router.push({
            name: 'appBaseInfo',
            params: {
              id: this.appCode,
              pluginTypeActive: true,
            },
          });
          break;

        // 未完善应用基本信息
        case 'FILL_EXTRA_INFO':
          this.$router.push({
            name: 'appBasicInfo',
            params: { id: this.appCode, moduleId: this.curModuleId },
          });
          break;
      }
    },

    /**
     * 应用下架
     */
    handleOfflineApp() {
      this.offlineAppDialog.visiable = true;
    },

    /**
     * 确认应用下架
     */
    async confirmOfflineApp() {
      this.offlineAppDialog.isLoading = true;
      try {
        const res = await this.$store.dispatch('deploy/offlineApp', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
        });

        this.$emit('appOfflineProgress', true);
        this.watchOfflineOperation(res.offline_operation_id);

        if (this.environment === 'prod') {
          this.appMarketPublished = false;
          this.$store.commit('updateCurAppMarketPublished', false);
        }
      } catch (e) {
        this.$emit('appOfflineProgress', false);
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('下架失败，请稍候再试'),
        });
      } finally {
        this.offlineAppDialog.visiable = false;
        this.offlineAppDialog.isLoading = false;
      }
    },

    cancelOfflineApp() {
      this.offlineAppDialog.visiable = false;
      this.offlineAppDialog.isLoading = false;
    },

    handleOpenLink() {
      window.open(this.exposedLink);
    },

    handleClearDeploy() {
      this.isWatchDeploying = false;
      this.isWatchOfflineing = false;
      this.isDeploySuccess = false;
      this.isDeployFail = false;
      this.isDeployInterrupted = false;
      this.isDeployInterrupting = false;
      this.isDeploySseEof = true;

      // 清空成本参数
      this.costConf.enable = false;
      this.costConf.hour = '';
      this.costConf.minute = '';

      this.deployStartTimeQueue = [];
      this.deployEndTimeQueue = [];
      this.deployTotalTime = 0;

      // 重置状态
      this.$refs.deployTimelineRef && this.$refs.deployTimelineRef.handleResetStatus();
    },

    async handleFailCallback() {
      await this.getLastDeployHistory();
      this.handleClearDeploy();
    },

    handleSuccessCallback() {
      this.getLastDeployHistory();
      this.handleClearDeploy();
    },

    /**
     * 轮询获取应用下架进度
     */
    watchOfflineOperation(offlineOperationId) {
      this.isWatchOfflineing = true;
      this.offlineTimer = setInterval(async () => {
        try {
          const res = await this.$store.dispatch('deploy/getOfflineResult', {
            appCode: this.appCode,
            moduleId: this.curModuleId,
            offlineOperationId,
          });

          // 下架进行中，三状态：pendding successful failed，pendding需要继续轮询
          if (res.status === 'successful') {
            this.isWatchOfflineing = false;
            this.getModuleReleaseInfo();
            this.$paasMessage({
              theme: 'success',
              message: this.$t('应用下架成功'),
            });
            bus.$emit('update_entrance');
            clearInterval(this.offlineTimer);
          } else if (res.status === 'failed') {
            const message = res.err_detail;
            this.isWatchOfflineing = false;
            this.$paasMessage({
              theme: 'error',
              message,
            });
            clearInterval(this.offlineTimer);
          }
        } catch (e) {
          this.isWatchOfflineing = false;
          clearInterval(this.offlineTimer);
          this.$paasMessage({
            theme: 'error',
            message: e.detail || e.message || this.$t('下架失败，请稍候再试'),
          });
        }
      }, 3000);
    },

    /**
     * 检测模块下架进度状况，如果进行中需要拉起“获取模块下架进度”
     */
    async checkOfflineOperation() {
      try {
        const res = await this.$store.dispatch('deploy/getOfflineStatus', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
        });

        const { result } = res;
        if (result && result.id) {
          this.$paasMessage({
            theme: 'primary',
            message: this.$t('检测到未结束的下架操作，进度已恢复'),
          });
          this.watchOfflineOperation(result.id);
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      }
    },

    /**
     * 检测模块部署进度状况
     */
    async checkDeployOperation() {
      try {
        const res = await this.$store.dispatch('deploy/getDeployStatus', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
        });
        if (res && res.deployment_id) {
          this.$paasMessage({
            theme: res.has_requested_int ? 'warning' : 'primary',
            message: this.$t('检测到尚未结束的部署任务，已恢复部署进度'),
          });
          this.reConnectTimes = 0;
          this.branchSelection = `${res.repo.type}:${res.repo.name}`;
          this.curDeployId = this.formatRevision(res.repo.revision);
          this.watchDeployStatus(res.deployment_id);
          this.deploymentId = res.deployment_id;

          if (res.has_requested_int) {
            this.isWatchDeploying = false;
            this.isDeployInterrupting = true;
          }
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        setTimeout(() => {
          this.isLoading = false;
        }, 500);
      }
    },

    /**
     * 获取应用文档列表
     */
    async getAppDocLinks() {
      try {
        const res = await this.$store.dispatch('deploy/getAppDocLinks', {
          appCode: this.appCode,
          params: {
            plat_panel: 'app_deployment',
            limit: 4,
          },
        });
        const links = res.links.map((link) => ({
          text: link.title,
          value: link.location,
        }));
        this.curTimeline = {
          displayBlocks: [
            {
              name: this.$t('帮助文档'),
              type: 'link',
              key: 'default',
              infos: links,
            },
          ],
        };
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      }
    },

    /**
     * 获取部署前各阶段详情
     */
    async getPreDeployDetail() {
      try {
        const res = await this.$store.dispatch('deploy/getPreDeployDetail', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
        });
        const timeLineList = [];
        res.forEach((stageItem) => {
          timeLineList.push({
            // name: 部署阶段的名称
            name: stageItem.type,
            // tag: 部署阶段的展示名称
            tag: stageItem.display_name,
            // content: 完成时间
            content: '',
            // status: 部署阶段的状态
            status: 'default',
            displayBlocks: this.formatDisplayBlock(stageItem.display_blocks),
            // stage: 部署阶段类型, 仅主节点有该字段
            stage: stageItem.type,
            // sse没返回子进程的状态时强行改变当前的进程状态为 pending 的标识
            loading: false,
          });

          stageItem.steps.forEach((stepItem) => {
            timeLineList.push({
              // name: 部署阶段的名称
              name: stepItem.name,
              // tag: 部署阶段的展示名称
              tag: stepItem.display_name,
              // content: 完成时间
              content: '',
              // status: 部署阶段的状态
              status: 'default',
              parent: stageItem.display_name,
              parentStage: stageItem.type,
            });
          });
        });
        this.timeLineList = timeLineList;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      }
    },

    // 获取进程列表
    async getProcessList(releaseId, isLoading = false) {
      this.closeServerPush();
      this.processLoading = isLoading;
      try {
        const res = await this.$store.dispatch('processes/getLastVersionProcesses', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: this.environment,
          releaseId,
        });
        this.formatProcesses(res);
        // 发起服务监听
        this.watchServerPush();
      } catch (e) {
        // 无法获取进程目前状态
        console.error(e);
        // this.$paasMessage({
        //     theme: 'error',
        //     message: '查询进程状态失败，请稍后再试。'
        // })
      } finally {
        this.processLoading = false;
        // if (!this.fetchProcessTimer && isLoop) {
        //     this.fetchProcessTimer = setInterval(() => {
        //         this.getProcessList(releaseId, isLoop)
        //     }, 3000)
        // }
      }
    },

    closeServerPush() {
      // 把当前服务监听关闭
      if (this.serverProcessEvent) {
        this.serverProcessEvent.close();
      }
    },

    // 对数据进行处理
    formatProcesses(processesData) {
      const allProcesses = [];
      // const tempArray = []
      // this.allProcesses = []

      // 保存上次的版本号
      this.prevProcessVersion = processesData.processes.metadata.resource_version;
      this.prevInstanceVersion = processesData.instances.metadata.resource_version;

      // 遍历进行数据组装
      const extraInfos = processesData.processes.extra_infos;
      const packages = processesData.process_packages;
      const instances = processesData.instances.items;

      processesData.processes.items.forEach((processItem) => {
        const { type } = processItem;
        const extraInfo = extraInfos.find((item) => item.type === type);
        const packageInfo = packages.find((item) => item.name === type);

        const processInfo = {
          ...processItem,
          ...packageInfo,
          ...extraInfo,
          instances: [],
        };

        instances.forEach((instance) => {
          if (instance.process_type === type) {
            processInfo.instances.push(instance);
          }
        });

        // 状态设置
        // let operateIconTitle = '停止进程'
        // if (processInfo.instances.length === 0) {
        //     operateIconTitle = '启动进程'
        // }
        // if (this.isAppOfflined) {
        //     operateIconTitle = '模块已下架，不可操作'
        // }

        // 作数据转换，以兼容原逻辑
        const process = {
          name: processInfo.name,
          instance: processInfo.instances.length,
          instances: processInfo.instances,
          targetReplicas: processInfo.target_replicas,
          isStopTrigger: false,
          targetStatus: processInfo.target_status,
          isActionLoading: false, // 用于记录进程启动/停止接口是否已完成
          maxReplicas: processInfo.max_replicas,
          status: 'Stopped',
          cmd: processInfo.command,
          // operateIconTitle: operateIconTitle,
          // operateIconTitleCopy: operateIconTitle,
          // isShowTooltipConfirm: false,
          desired_replicas: processInfo.replicas,
          available_instance_count: processInfo.success,
          failed: processInfo.failed,
          resourceLimit: processInfo.resource_limit,
          clusterLink: processInfo.cluster_link,

          // instanceLogLoading: false,
          // instanceLogs: [],
          // expanded: false
        };

        // this.$set(process, 'instanceLogLoading', false)
        // this.$set(process, 'instanceLogs', [])
        this.$set(process, 'expanded', false);

        // this.updateProcessStatus(process)

        // 日期转换
        process.instances.forEach((item) => {
          item.date_time = moment(item.start_time).startOf('minute').fromNow();
        });

        // 如果有当前展开项
        // if (this.curProcessKey && this.curProcessKey === processInfo.name) {
        //     this.curProcess = process
        // }

        // this.allProcesses.push(process)
        allProcesses.push(process);
      });

      // allProcesses.forEach(item => {
      //     item.instances.forEach(instanceItem => {
      //         tempArray.push({
      //             ...item,
      //             state: instanceItem.state,
      //             instanceData: { ...instanceItem }
      //         })
      //     })
      // })

      // this.allProcesses.splice(0, this.allProcesses.length, ...tempArray)

      // this.allProcesses.splice(0, this.allProcesses.length, ...allProcesses)
      this.allProcesses = JSON.parse(JSON.stringify(allProcesses));
    },

    updateProcessStatus(process) {
      /*
       * 设置进程状态
       * targetStatus: 进行的操作，start\stop\scale
       * status: 操作状态，Running\stoped
       *
       * 如何判断进程当前是否为操作中（繁忙状态）？
       * 主要根据 process_packages 里面的 target_status 判断：
       * 如果 target_status 为 stop，仅当 processes 里面的 success 为 0 且实例为 0 时正常，否则为操作中
       * 如果 target_status 为 start，仅当 success 与 target_replicas 一致，而且 failed 为 0 时正常，否则为操作中
       */
      if (process.targetStatus === 'stop') {
        // process.operateIconTitle = '启动进程'
        // process.operateIconTitleCopy = '启动进程'
        if (process.available_instance_count === 0 && process.instances.length === 0) {
          process.status = 'Stopped';
        } else {
          process.status = 'Running';
        }
      } else if (process.targetStatus === 'start') {
        // process.operateIconTitle = '停止进程'
        // process.operateIconTitleCopy = '停止进程'
        if (process.available_instance_count === process.targetReplicas && process.failed === 0) {
          process.status = 'Stopped';
        } else {
          process.status = 'Running';
        }
      }
    },

    // 更新进程
    updateProcessData(data) {
      const processData = data.object || {};
      this.prevProcessVersion = data.resource_version || 0;

      if (data.type === 'ADDED') {
        this.getProcessList(this.releaseId, false);
      } else if (data.type === 'MODIFIED') {
        this.allProcesses.forEach((process) => {
          if (process.name === processData.type) {
            process.available_instance_count = processData.success;
            process.desired_replicas = processData.replicas;
            process.failed = processData.failed;
            this.updateProcessStatus(process);
          }
        });
      } else if (data.type === 'DELETED') {
        this.allProcesses = this.allProcesses.filter((process) => process.name !== processData.type);
      }
    },

    // 更新实例
    updateInstanceData(data) {
      const instanceData = data.object || {};
      this.prevInstanceVersion = data.resource_version || 0;

      instanceData.date_time = moment(instanceData.start_time).startOf('minute').fromNow();
      this.allProcesses.forEach((process) => {
        if (process.name === instanceData.process_type) {
          // 新增
          if (data.type === 'ADDED') {
            // 防止在短时间内重复推送
            // process.instances.forEach((instance, index) => {
            //     if (instance.name === instanceData.name) {
            //         process.instances.splice(index, 1)
            //     }
            // })
            // process.instances.push(instanceData)
          } else {
            process.instances.forEach((instance, index) => {
              if (instance.name === instanceData.name) {
                if (data.type === 'DELETED') {
                  // 删除
                  process.instances.splice(index, 1);
                } else {
                  // 更新
                  process.instances.splice(index, 1, instanceData);
                }
              }
            });
          }

          this.updateProcessStatus(process);
        }
      });
    },

    watchServerPush() {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/envs/${this.environment}/processes/watch/?rv_proc=${this.prevProcessVersion}&rv_inst=${this.prevInstanceVersion}&timeout_seconds=${this.serverTimeout}`;
      this.serverProcessEvent = new EventSource(url, {
        withCredentials: true,
      });

      // 收藏服务推送消息
      this.serverProcessEvent.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.warn(data);
        if (data.object_type === 'process') {
          this.updateProcessData(data);
        } else if (data.object_type === 'instance') {
          this.updateInstanceData(data);
          if (data.type === 'ADDED') {
            console.warn(this.$t('重新拉取进程...'));
            this.getProcessList(this.releaseId, false);
          }
        } else if (data.type === 'ERROR') {
          // 判断 event.type 是否为 ERROR 即可，如果是 ERROR，就等待 2 秒钟后，重新发起 list/watch 流程
          clearTimeout(this.timer);
          this.timer = setTimeout(() => {
            this.getProcessList(this.releaseId, false);
          }, 2000);
        }
      };

      // 服务异常
      this.serverProcessEvent.onerror = (event) => {
        // 异常后主动关闭，否则会继续重连
        console.error(this.$t('推送异常'), event);
        this.serverProcessEvent.close();

        clearTimeout(this.serverEventErrorTimer);
        // 推迟调用，防止过于频繁导致服务性能问题
        this.serverEventErrorTimer = setTimeout(() => {
          this.watchServerPush();
        }, 3000);
      };

      // 服务结束
      this.serverProcessEvent.addEventListener('EOF', (_event) => {
        this.serverProcessEvent.close();

        if (!this.isDeploySseEof) {
          clearTimeout(this.serverEventEOFTimer);
          // 推迟调用，防止过于频繁导致服务性能问题
          this.serverEventEOFTimer = setTimeout(() => {
            this.watchServerPush();
          }, 3000);
        }
      });
    },

    formatDisplayBlock(displays) {
      const displayBlocks = [];
      const keys = Object.keys(displays);
      for (const key of keys) {
        const sourceInfo = [];
        if (displays[key].display_name) {
          sourceInfo.push({
            text: this.$t('类型'),
            value: displays[key].display_name,
          });
        }
        if (displays[key].repo_url) {
          sourceInfo.push({
            text: this.$t('地址'),
            value: displays[key].repo_url,
          });
        }
        if (displays[key].source_dir) {
          sourceInfo.push({
            text: this.$t('部署目录'),
            value: displays[key].source_dir,
          });
        }
        if (this.curAppInfo.application.is_plugin_app) {
          sourceInfo.push({
            text: this.$t('模块类型'),
            value: this.$t('蓝鲸插件'),
            href: this.GLOBAL.LINK.BK_PLUGIN,
            hrefText: this.$t('查看详情'),
          });
        }

        // 普通应用不展示
        if (
          this.curAppModule.web_config.templated_source_enabled &&
          this.curAppModule.source_origin !== this.GLOBAL.APP_TYPES.NORMAL_APP
        ) {
          sourceInfo.push(
            {
              text: this.$t('初始化模板类型'),
              value: this.initTemplateTypeDisplay || '--',
            },
            {
              text: this.$t('初始化模板说明'),
              value: this.initTemplateDesc || '--',
              downloadBtn: this.handleDownloadTemplate,
              downloadBtnText: this.initTemplateDesc === '--' ? '' : this.$t('下载模板代码'),
            }
          );
        }

        if (this.curAppModule.web_config.runtime_type !== 'custom_image') {
          const smartRoute = [
            {
              name: this.$t('查看包版本'),
              route: {
                name: 'appPackages',
              },
            },
          ];
          const value = this.isSmartApp
            ? smartRoute
            : this.curAppModule.source_origin === 1
            ? this.$t('代码库')
            : this.$t('蓝鲸运维开发平台提供源码包');
          // 普通应用不展示
          if (this.curAppModule.source_origin !== this.GLOBAL.APP_TYPES.NORMAL_APP) {
            sourceInfo.push({
              text: this.$t('源码管理'),
              value,
            });
          }
        }

        switch (key) {
          // 源码信息
          case 'source_info':
            displayBlocks.push({
              name:
                this.curAppModule.web_config.runtime_type === 'custom_image'
                  ? this.$t('镜像信息')
                  : this.$t('源码信息'),
              type: 'key-value',
              routerName: 'moduleManage',
              key,
              infos: sourceInfo,
            });
            break;

          // 增强服务
          case 'services_info':
            displayBlocks.push({
              name: this.$t('增强服务'),
              type: 'key-value',
              key,
              infos: [
                {
                  text: this.$t('启用未创建'),
                  value: displays[key]
                    .filter((item) => !item.is_provisioned)
                    .map((item) => item.display_name)
                    .join(', '),
                },
                {
                  text: this.$t('已创建实例'),
                  value: displays[key]
                    .filter((item) => item.is_provisioned)
                    .map((item) => ({
                      name: item.display_name,
                      route: {
                        name: 'appServiceInner',
                        params: {
                          id: this.appCode,
                          service: item.service_id,
                          category_id: item.category_id,
                        },
                      },
                    })),
                },
              ],
            });
            break;

          // 运行时的信息
          case 'runtime_info':
            displayBlocks.push({
              name: this.$t('运行时信息'),
              type: 'key-value',
              routerName: 'appEnvVariables',
              key,
              infos: [
                {
                  text: this.$t('基础镜像'),
                  value: displays[key].image,
                },
                {
                  text: this.$t('构建工具'),
                  value: displays[key].buildpacks.map((item) => item.display_name).join(', '),
                },
              ],
            });
            break;

          // 访问地址
          case 'access_info':
            displayBlocks.push({
              name: this.$t('访问地址'),
              type: 'key-value',
              routerName: 'appEntryConfig',
              key,
              infos: [
                {
                  text: this.$t('当前类型'),
                  value:
                    displays[key] && displays[key].type === 'default_subdomain' ? this.$t('子域名') : this.$t('子路径'),
                },
                {
                  text: this.$t('访问地址'),
                  value: displays[key].address,
                },
              ],
            });
            break;

          // 帮助文档
          case 'prepare_help_docs':
          case 'build_help_docs':
          case 'release_help_docs':
            displayBlocks.push({
              name: this.$t('帮助文档'),
              type: 'link',
              key,
              infos: displays[key].map((doc) => ({
                text: doc.name,
                value: doc.link,
              })),
            });
            break;
        }
      }
      return displayBlocks;
    },

    /**
     * 创建svn分支
     */
    async handleCreateBranch() {
      if (this.createBranchLoading) {
        return false;
      }
      this.createBranchLoading = true;
      try {
        const res = await this.$store.dispatch('deploy/createSvnBranch', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        const branchName = res.request_data.tag_name;
        this.$paasMessage({
          theme: 'success',
          message: `${this.$t('已成功创建新分支：')}${branchName}`,
        });
        this.getModuleBranches(`branch:${branchName}`);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          delay: 10000,
          message: e.detail || e.message,
        });
      } finally {
        this.createBranchLoading = false;
      }
    },

    stopDeploy() {
      if (this.appearDeployState.includes('build')) {
        this.stopDeployConf.title = this.$t('确认停止【构建阶段】吗？');
        this.stopDeployConf.stage = 'build';
      }

      if (this.appearDeployState.includes('release')) {
        this.stopDeployConf.title = this.$t('确认停止【部署阶段】吗？');
        this.stopDeployConf.stage = 'release';
      }
      this.stopDeployConf.visiable = true;
    },

    async confirmStopDeploy() {
      try {
        await this.$store.dispatch('deploy/stopDeploy', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          deployId: this.deploymentId,
        });
        this.isDeployInterrupting = true;
        this.isWatchDeploying = false;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('部署失败，请稍候再试'),
        });
      }
    },

    cancelStopDeploy() {
      this.stopDeployConf.visiable = false;
    },

    afterLeaveStopDeploy() {
      this.stopDeployConf.title = '';
      this.stopDeployConf.stage = '';
    },

    /**
     * 跳转到进程详情页面
     */
    goProcessView() {
      this.$router.push({
        name: 'appProcess',
        params: {
          id: this.appCode,
          moduleId: this.curModuleId,
        },
        query: {
          focus: this.environment,
        },
      });
    },

    /**
     * 获取基本模块信息
     */
    async fetchModuleInfo() {
      try {
        const res = await this.$store.dispatch('module/getModuleBasicInfo', {
          appCode: this.curAppInfo.application.code,
          modelName: this.curAppModule.name,
        });
        this.initLanguage = res.language;
        this.initTemplateType = res.template_display_name;
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.message,
        });
      }
    },

    /**
     * 初始化模板说明
     */
    async fetchLanguageInfo() {
      try {
        const res = await this.$store.dispatch('module/getLanguageInfo');
        const { region } = this.curAppModule;

        this.initTemplateDesc = '';
        if (res[region] && res[region].languages) {
          const languages = res[region].languages[this.initLanguage] || [];
          const lanObj = languages.find((item) => item.display_name === this.initTemplateType) || {};
          this.initTemplateDesc = lanObj.description || '--';
        }
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.message,
        });
      }
    },

    /**
     * 下载模板说明
     */
    async handleDownloadTemplate() {
      try {
        const res = await this.$store.dispatch('getAppInitTemplateUrl', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        fileDownload(res.downloadable_address);
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: resp.detail || this.$t('服务暂不可用，请稍后再试'),
        });
      }
    },

    dropdownShow() {
      this.isDropdownShow = true;
    },
    dropdownHide() {
      this.isDropdownShow = false;
    },

    changeTime(time) {
      const dateTimeStamp = new Date(time).getTime();

      const minute = 1000 * 60;
      const hour = minute * 60;
      const day = hour * 24;

      const month = day * 30;
      const year = month * 12;
      const now = new Date().getTime();
      const diffValue = now - dateTimeStamp;
      let result = '';
      if (diffValue < 0) {
        return;
      }

      const monthC = diffValue / month;
      const weekC = diffValue / (7 * day);
      const dayC = diffValue / day;
      const hourC = diffValue / hour;
      const minC = diffValue / minute;
      const yearC = diffValue / year;
      if (yearC >= 1) {
        return `${parseInt(yearC)}${this.$t('年前')}`;
      }
      if (monthC >= 1) {
        result = `${parseInt(monthC)}${this.$t('月前')}`;
      } else if (weekC >= 1) {
        result = `${parseInt(weekC)}${this.$t('周前')}`;
      } else if (dayC >= 1) {
        result = `${parseInt(dayC)}${this.$t('天前')}`;
      } else if (hourC >= 1) {
        result = `${parseInt(hourC)}${this.$t('小时前')}`;
      } else if (minC >= 1) {
        result = `${parseInt(minC)}${this.$t('分钟前')}`;
      } else {
        result = this.$t('刚刚');
      }

      return result;
    },

    getBranchInfoType() {
      const branchInfo = this.branchesMap[this.branchSelection];
      this.branchInfoType = branchInfo.display_type;
    },

    async getLessCode() {
      try {
        const resp = await this.$store.dispatch('baseInfo/gitLessCodeAddress', {
          appCode: this.appCode,
          moduleName: this.curModuleId,
        });
        if (resp.address_in_lesscode === '' && resp.tips === '') {
          this.lessCodeFlag = false;
        }
        this.lessCodeData = resp;
      } catch (errRes) {
        this.lessCodeFlag = false;
        console.error(errRes);
      }
    },

    handleLessCode() {
      if (this.lessCodeData.address_in_lesscode) {
        return;
      }
      this.$bkMessage({ theme: 'warning', message: this.lessCodeData.tips, delay: 2000, dismissable: false });
    },
  },
};
</script>

<style lang="scss" scoped>
.dropdown-trigger-btn-branch {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #c4c6cc;
  height: 32px;
  min-width: 68px;
  border-radius: 2px;
  padding: 0 15px;
  color: #63656e;
}
.dropdown-trigger-btn.bk-icon {
  font-size: 18px;
}
.dropdown-trigger-btn .bk-icon {
  font-size: 22px;
}
.dropdown-trigger-btn:hover {
  cursor: pointer;
  border-color: #979ba5;
}
.framework-wrapper {
  margin-top: -10px;
}
.error-wrapper {
  padding: 8px 15px 8px 35px;
  color: #666666;
}
.ps-tip-block::after {
  top: 9px;
  font-size: 14px;
}
</style>
<style>
.operate {
  display: inline-block;
}
.operate .medium-font .bk-dropdown-trigger {
  position: relative;
  top: 2px;
}
.mirrorInfo {
  font-size: 12px;
  margin-left: 23px;
  color: #979ba5;
}
.error-tip {
  font-size: 12px;
  color: #ea3636;
  line-height: 18px;
  margin-top: 2px;
}
.remove-module-dialog-cls {
  z-index: 9999 !important;
}
</style>

<style lang="scss" scoped>
@import './index.scss';
</style>
