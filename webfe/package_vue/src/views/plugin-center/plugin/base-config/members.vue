<template lang="html">
  <div class="right-main">
    <paas-content-loader
      class="app-container middle"
      :is-loading="loading"
      placeholder="roles-loading"
    >
      <paas-plugin-title />
      <div class="header mt10 header-flex">
        <span v-bk-tooltips.top="{ content: $t('仅管理员可添加成员'), disabled: canManageMembers }">
          <bk-button
            theme="primary"
            icon="plus"
            :disabled="!canManageMembers"
            @click="createMember"
          >
            {{ $t('新增成员') }}
          </bk-button>
        </span>
        <bk-input
          v-model="keyword"
          class="search-input"
          :placeholder="$t('请输入')"
          :clearable="true"
          :right-icon="'bk-icon icon-search'"
          @enter="handleSearch"
        />
      </div>
      <div class="content-wrapper">
        <bk-table
          v-bkloading="{ isLoading: isTableLoading }"
          :data="memberListShow"
          size="small"
          :pagination="pagination"
          :outer-border="false"
          :header-border="false"
          @page-change="pageChange"
          @page-limit-change="limitChange"
        >
          <div
            v-if="memberListShow.length"
            slot="empty"
          >
            <bk-exception
              class="exception-wrap-item exception-part"
              type="search-empty"
              scene="part"
            />
            <div class="empty-tips">
              {{ $t('可以尝试调整关键词 或') }}
              <span
                class="clear-search"
                @click="clearFilterKey"
              >{{ $t('清空搜索条件') }}</span>
            </div>
          </div>
          <bk-table-column :label="$t('成员姓名')">
            <template slot-scope="props">
              <span
                v-if="props.row.avatar"
                class="user-photo"
              ><img :src="props.row.avatar"></span>
              <span class="user-name">{{ props.row.username }}</span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('角色')">
            <template slot-scope="props">
              <span class="role-name">{{ $t(roleNames[props.row.role.roleName]) }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('权限')"
            min-width="170"
          >
            <template slot-scope="props">
              <span
                v-for="(perm, permIndex) in roleSpec[props.row.role.roleName]"
                v-if="perm[Object.keys(perm)[0]]"
                :key="permIndex"
              >
                {{ $t(Object.keys(perm)[0]) }}<span v-if="props.row.role.roleName === 'administrator' && permIndex !== 2">{{ localLanguage === 'en' ? ', ' : '、' }}</span>
              </span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('操作')">
            <template slot-scope="props">
              <template v-if="isCurrentUser(props.row)">
                <span v-bk-tooltips.top="{ content: $t('插件至少有一个管理员'), disabled: !signoutDisabled }">
                  <bk-button
                    text
                    class="mr5"
                    :disabled="signoutDisabled"
                    @click="showLeavePluginDialog(props.row.role.id, props.row.username)"
                  >
                    {{ $t('退出插件') }}
                  </bk-button>
                </span>
              </template>
              <bk-button
                v-if="canManageMembers"
                text
                class="mr5"
                @click="updateMember(props.row.role.id, props.row.username, props.row.role.roleName)"
              >
                {{ $t('更换角色') }}
              </bk-button>
              <bk-button
                v-if="canManageMembers && !isCurrentUser(props.row)"
                text
                class="mr5"
                @click="delMember(props.row.username, props.row.role.id)"
              >
                {{ $t('删除成员') }}
                <round-loading
                  v-if="isDelLoading && selectedMember.name === props.row.username"
                  class="loading-transform"
                />
              </bk-button>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </paas-content-loader>

    <bk-dialog
      v-model="memberMgrConfig.visiable"
      width="600"
      :title="memberMgrConfig.title"
      header-position="left"
      :theme="'primary'"
      :mask-close="false"
      :loading="memberMgrConfig.isLoading"
      @confirm="memberMgrSave"
      @cancel="closeMemberMgrModal"
      @after-leave="hookAfterClose"
    >
      <div
        v-if="memberMgrConfig.showForm"
        style="min-height: 130px;"
      >
        <bk-form
          :label-width="120"
          form-type="vertical"
        >
          <bk-form-item
            :label="$t('成员名称')"
            :required="true"
          >
            <template v-if="memberMgrConfig.userEditable">
              <user v-model="personnelSelectorList" />
              <!-- <bk-member-selector
                                @change="updateValue"
                                v-model="personnelSelectorList"
                                ref="member_selector">
                            </bk-member-selector> -->
            </template>
            <template v-else>
              <bk-input
                v-model="selectedMember.name"
                :readonly="true"
              />
            </template>
          </bk-form-item>
          <bk-form-item
            :label="$t('角色')"
            :required="true"
          >
            <bk-radio-group v-model="roleName">
              <bk-radio
                v-for="(chineseName, name) in roleNames"
                :key="name"
                :value="name"
              >
                {{ $t(chineseName) }}
              </bk-radio>
            </bk-radio-group>
          </bk-form-item>
          <bk-form-item label="">
            <div class="ps-rights-list">
              <span :class="`pointer-icon ${developerClass}`" />
              <!-- roleName 当前权限 -->
              <span class="ps-rights-title">{{ $t('权限列表') }}</span>
              <span
                v-for="(perm, permIndex) in roleSpec[roleName]"
                :key="permIndex"
              >
                <a
                  v-if="perm[Object.keys(perm)[0]]"
                  class="available-right"
                >
                  <span>{{ $t(Object.keys(perm)[0]) }}</span>
                </a>
                <a
                  v-else
                  class="not-available-right"
                >
                  <span>{{ $t(Object.keys(perm)[0]) }}</span>
                </a>
              </span>
            </div>
          </bk-form-item>
        </bk-form>
      </div>
    </bk-dialog>
  </div>
</template>

<script>
    import auth from '@/auth';
    import pluginBaseMixin from '@/mixins/plugin-base-mixin';
    import user from '@/components/user';
    import paasPluginTitle from '@/components/pass-plugin-title';

    const ROLE_BACKEND_IDS = {
        'administrator': 2,
        'developer': 3
    };

    const ROLE_ID_TO_NAME = {
        2: 'administrator',
        3: 'developer'
    };

    const PLUGIN_ROLE_NAMES = {
        'administrator': '管理员',
        'developer': '开发者'
    };

    const ROLE_SPEC_PLUGIN = {
        'administrator': [
            {
                '插件开发': true
            },
            {
                '上线审核': true
            },
            {
                '成员管理': true
            }
        ],
        'developer': [
            {
                '插件开发': true
            },
            {
                '上线审核': false
            },
            {
                '成员管理': false
            }
        ]
    };

    export default {
        components: {
            user,
            paasPluginTitle
        },
        mixins: [pluginBaseMixin],
        data () {
            return {
                currentUser: auth.getCurrentUser().username,
                loading: true,
                memberList: [],
                memberListShow: [],
                roleNames: PLUGIN_ROLE_NAMES,
                roleSpec: ROLE_SPEC_PLUGIN,
                roleName: 'administrator',
                selectedMember: {
                    id: 0,
                    name: ''
                },
                personnelSelectorList: [],
                memberMgrConfig: {
                    visiable: false,
                    isLoading: false,
                    type: 'create',
                    userEditable: true,
                    title: this.$t('新增成员'),
                    showForm: false
                },
                pagination: {
                    current: 1,
                    count: 0,
                    limit: 10
                },
                currentBackup: 1,
                enableToAddRole: false,
                keyword: '',
                memberListClone: [],
                isTableLoading: false,
                isDelLoading: false
            };
        },
        computed: {
            // 当前用户是否为当前插件的管理员
            canManageMembers () {
                const curUserData = this.memberListShow.find(item => item.username === this.currentUser) || {};
                return curUserData.role && curUserData.role.id === ROLE_BACKEND_IDS['administrator'];
            },
            signoutDisabled () {
                const adminUsers = this.memberListShow.filter(user => user.role.roleName === 'administrator');
                return adminUsers.length <= 1;
            },
            localLanguage () {
                return this.$store.state.localLanguage;
            },
            developerClass () {
                if (this.roleName === 'developer') {
                    return this.localLanguage === 'en' ? 'en-developer-left' : 'developer';
                }
                return this.localLanguage === 'en' ? 'en-icon-left' : '';
            }
        },
        watch: {
            '$route' () {
                this.init();
            },
            'pagination.current' (value) {
                this.currentBackup = value;
            },
            keyword (val) {
                if (!val) {
                    this.handleSearch();
                }
            }
        },
        created () {
            this.init();
        },
        methods: {
            pageChange (page) {
                if (this.currentBackup === page) {
                    return;
                }
                this.pagination.current = page;

                this.handleSearch();
                // const start = this.pagination.limit * (this.pagination.current - 1)
                // const end = start + this.pagination.limit
                // this.memberListShow.splice(0, this.memberListShow.length, ...this.memberList.slice(start, end))
            },

            limitChange (currentLimit, prevLimit) {
                this.pagination.limit = currentLimit;
                this.pagination.current = 1;

                this.handleSearch();

                // const start = this.pagination.limit * (this.pagination.current - 1)
                // const end = start + this.pagination.limit
                // this.memberListShow.splice(0, this.memberListShow.length, ...this.memberList.slice(start, end))
            },

            updateValue (curVal) {
                curVal ? this.personnelSelectorList = curVal : this.personnelSelectorList = '';
            },

            init () {
                this.enableToAddRole = this.curPluginInfo && this.curPluginInfo.role && this.curPluginInfo.role.id === ROLE_BACKEND_IDS['administrator'];
                this.fetchMemberList();
            },

            async fetchMemberList () {
                this.isTableLoading = true;
                try {
                    const res = await this.$store.dispatch('pluginMembers/getMemberList', { pdId: this.pdId, pluginId: this.pluginId });
                    this.pagination.count = res.length;
                    res.forEach(element => {
                        this.$set(element.role, 'roleName', ROLE_ID_TO_NAME[element.role.id]);
                    });
                    const start = this.pagination.limit * (this.pagination.current - 1);
                    const end = start + this.pagination.limit;
                    this.memberList.splice(0, this.memberList.length, ...(res || []));
                    this.memberListShow.splice(0, this.memberListShow.length, ...this.memberList.slice(start, end));
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || this.$t('接口异常')
                    });
                } finally {
                    this.loading = false;
                    this.isTableLoading = false;
                }
            },

            createMember () {
                this.roleName = 'administrator';
                this.personnelSelectorList = [];
                this.memberMgrConfig = {
                    visiable: true,
                    isLoading: false,
                    type: 'create',
                    userEditable: true,
                    title: this.$t('新增成员'),
                    showForm: true
                };
            },

            hookAfterClose () {
                this.memberMgrConfig.showForm = false;
            },

            async createSave () {
                this.memberMgrConfig.isLoading = true;
                if (!this.personnelSelectorList.length) {
                    this.$paasMessage({
                        theme: 'error',
                        message: this.$t('请选择成员！')
                    });
                    setTimeout(() => {
                        this.memberMgrConfig.isLoading = false;
                    }, 100);
                    return;
                }

                let createParam = {};
                const createSuc = [];
                for (let i = 0; i < this.personnelSelectorList.length; i++) {
                    createParam = {
                        'username': this.personnelSelectorList[i],
                        'role': {
                            'id': ROLE_BACKEND_IDS[this.roleName]
                        }
                    };
                    createSuc.push(createParam);
                }
                try {
                    await this.$store.dispatch('pluginMembers/addMember', {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        postParams: createSuc
                    });
                    this.closeMemberMgrModal();
                    this.fetchMemberList();
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('新增成员成功！')
                    });
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: `${this.$t('添加用户角色失败：')} ${e.detail}`
                    });
                } finally {
                    this.memberMgrConfig.isLoading = false;
                }
            },

            showLeavePluginDialog (delMemberID, delMemberName) {
                this.selectedMember.id = delMemberID;
                this.selectedMember.name = delMemberName;
                this.$bkInfo({
                    title: this.$t(`确认退出并放弃此插件的权限？`),
                    width: 480,
                    maskClose: true,
                    confirmFn: () => {
                        this.doLeavePlugin();
                    }
                });
            },

            // 退出插件
            async doLeavePlugin () {
                try {
                    await this.$store.dispatch('pluginMembers/leavePlugin', { pdId: this.pdId, pluginId: this.pluginId });
                    // 退出插件跳转
                    this.$router.push({
                        path: '/'
                    });
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: `${this.$t('退出插件失败：')} ${e.detail}`
                    });
                }
            },

            updateMember (updateMemberID, updateMemberName, updateMemberRole) {
                this.selectedMember.id = updateMemberID;
                this.selectedMember.name = updateMemberName;
                this.roleName = updateMemberRole;
                this.memberMgrConfig = {
                    visiable: true,
                    isLoading: false,
                    type: 'edit',
                    userEditable: false,
                    title: this.$t('更换角色'),
                    showForm: true
                };
            },

            memberMgrSave () {
                const mgrType = this.memberMgrConfig.type;
                if (mgrType === 'edit') {
                    return this.updateSave();
                } else if (mgrType === 'create') {
                    return this.createSave();
                }
            },

            // 是否更新接口
            async updateSave () {
                const roleInfo = {
                    'id': ROLE_BACKEND_IDS[this.roleName]
                };
                this.memberMgrConfig.isLoading = true;
                try {
                    await this.$store.dispatch('pluginMembers/updateRole', {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        username: this.selectedMember.name,
                        params: roleInfo
                    });
                    this.closeMemberMgrModal();
                    this.fetchMemberList();
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('角色更新成功！')
                    });
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: `${this.$t('修改角色失败：')} ${e.detail}`
                    });
                } finally {
                    this.memberMgrConfig.isLoading = false;
                }
            },

            delMember (delMemberName, delMemberID) {
                if (this.isDelLoading && this.selectedMember.name === delMemberName) {
                    return;
                }
                this.selectedMember.id = delMemberID;
                this.selectedMember.name = delMemberName;
                this.$bkInfo({
                    title: `${this.$t('删除成员')} ${delMemberName}`,
                    subTitle: `${this.$t('用户')} ${delMemberName} ${this.$t('将失去此应用的对应权限，是否确定删除？')}`,
                    width: 520,
                    confirmFn: () => {
                        this.delSave();
                    }
                });
            },

            async delSave () {
                this.isDelLoading = true;
                try {
                    await this.$store.dispatch('pluginMembers/deleteRole', {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        username: this.selectedMember.name
                    });
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('删除成员成功！')
                    });
                    this.fetchMemberList();
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: `${this.$t('删除成员失败：')} ${e.detail}`
                    });
                } finally {
                    this.isDelLoading = false;
                }
            },

            closeMemberMgrModal () {
                this.memberMgrConfig.visiable = false;
            },

            // 判断给定的 memberInfo 是否当前登录用户, 控制是否展示退出插件
            isCurrentUser (memberInfo) {
                return memberInfo.username === this.currentUser;
            },

            handleSearch () {
                if (this.keyword) {
                    this.memberListShow = this.memberList.filter(apigw => {
                        return apigw.username.toLowerCase().indexOf(this.keyword.toLowerCase()) > -1;
                    });
                    this.memberListClone = [...this.memberListShow];
                    this.pagination.count = this.memberListClone.length;
                    if (this.memberListClone.length > 10) {
                        const start = this.pagination.limit * (this.pagination.current - 1);
                        const end = start + this.pagination.limit;
                        this.memberListShow.splice(0, this.memberListShow.length, ...this.memberListClone.slice(start, end));
                    }
                } else {
                    this.fetchMemberList();
                }
            },
            clearFilterKey () {
                this.keyword = '';
            }
        }
    };
</script>

<style lang="scss" scoped>
    .content-wrapper {
        margin-top: 16px;
    }
    .search-input {
         width: 360px;
         display: inline-block;
    }
    .user-photo {
        margin: 5px 0;
        display: inline-block;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        overflow: hidden;
        border: solid 1px #eaeaea;
        vertical-align: middle;

        img {
            width: 100%;
            height: 100%;
        }
    }

    .user-name {
        display: inline-block;
        padding-left: 10px;
        font-size: 14px;
        color: #63656E;
        vertical-align: middle;
    }
    .role-name {
        color: #63656E;
    }

    .ps-pr {
        padding-right: 15px;
        color: #63656E;
    }

    .middle {
        padding-top: 15px;
    }

    .ps-rights-list {
        height: 54px;
        line-height: 54px;
        background: #F5F7FA;
        padding-left: 24px;
        border-radius: 2px;

        .ps-rights-title {
            user-select: none;
            font-size: 14px;
            margin-right: 16px;
            color: #63656E;
        }

        a {
            margin-right: 7px;
            padding: 4px 8px;
            font-size: 12px;
            line-height: 1;
            color: #666;
            cursor: default;

            &.available-right {
                border: 1px solid rgba(58,132,255,0.30);
                background: #EDF4FF;
                color: #3A84FF;

                i {
                    color: #3A84FF;
                    transform: scale(.95);
                }
            }

            &.not-available-right {
                border: 1px solid #ddd;
                background: #FAFBFD;
                color: #ddd;

                i {
                    transform: scale(.75);
                }
            }

            i {
                display: inline-block;
                margin-left: 3px;
            }
        }
    }

    .header-flex {
        display: flex;
        justify-content: space-between;
        margin-bottom: 16px;
    }

    .detail-doc {
        color: #3A84FF;
        cursor: pointer;
    }

    .dev-name {
        font-weight: 700;
    }

    .pointer-icon {
        position: absolute;
        width: 14px;
        height: 14px;
        transform: rotateZ(45deg);
        background: #F5F7FA;
        top: -5px;
        left: 30px;
    }
    .en-icon-left {
        left: 50px !important;
    }

    .developer {
        left: 110px;
    }

    .en-developer-left {
        left: 168px !important;
    }

    .empty-tips {
        margin-top: 5px;
        color: #979BA5;
        .clear-search {
            cursor: pointer;
            color: #3a84ff;
        }
    }

    .loading-transform {
        transform: translateY(-2px);
    }
</style>

<style>
.bk-plugin-wrapper .exception-wrap-item .bk-exception-img.part-img {
    height: 130px;
}
.bk-plugin-wrapper .bk-table th .bk-table-column-filter-trigger.is-filtered {
    color: #3a84ff !important;
}
</style>

