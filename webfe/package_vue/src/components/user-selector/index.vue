<template>
  <bk-dialog
    v-model="isShowDialog"
    width="700"
    title=""
    :mask-close="false"
    draggable
    header-position="left"
    ext-cls="bk-add-member-dialog"
    @after-leave="handleAfterLeave">
    <div slot="header" class="title">
      {{ $t(title) }}
    </div>
    <div class="add-member-content-wrapper" v-bkloading="{ isLoading, opacity: 1 }" :style="style">
      <div v-show="!isLoading">
        <div class="left">
          <div class="search-input">
            <bk-select
              v-model="searchConditionValue"
              :clearable="false"
              :popover-width="150"
              style="flex: 0 0 130px;"
              @selected="handleConditionSelcted">
              <bk-option
                v-for="option in searchConditionList"
                :key="option.id"
                :id="option.id"
                :name="option.name">
              </bk-option>
            </bk-select>
            <bk-input
              v-model="keyword"
              :placeholder="$t(placeholder)"
              maxlength="64"
              :clearable="true"
              style="position: relative; left: -1px;"
              @keyup.enter.native="handleSearch"
              @keyup.up.native="handleKeyup"
              @keyup.down.native="handleKeydown">
            </bk-input>
          </div>
          <div
            class="member-tree-wrapper"
            v-bkloading="{ isLoading: treeLoading, opacity: 1 }">
            <template v-if="isShowMemberTree">
              <div class="tree">
                <tree
                  ref="userTreeRef"
                  :all-data="treeList"
                  style="height: 341px;"
                  :key="infiniteTreeKey"
                  @async-load-nodes="handleRemoteLoadNode"
                  @on-select="handleOnSelected">
                </tree>
              </div>
            </template>
            <template v-if="isShowSearchResult">
              <div class="search-content">
                <template v-if="isHasSeachResult">
                  <list
                    ref="searchedResultsRef"
                    :all-data="searchedResult"
                    :focus-index.sync="focusItemIndex"
                    style="height: 341px;"
                    @on-checked="handleSearchResultSelected">
                  </list>
                </template>
                <template v-if="isSeachResultEmpty">
                  <div class="search-empty-wrapper">
                    <img src="./images/empty-display.svg" alt="" />
                    <p class="empty-tips"> {{ $t('搜索无结果') }} </p>
                  </div>
                </template>
              </div>
            </template>
          </div>
        </div>
        <div class="right">
          <div class="header">
            <div class="has-selected"> {{ $t('已选择') }} <template v-if="isShowSelectedText">
              <span class="organization-count">
                {{ hasSelectedDepartments.length }}
              </span> {{ $t('个组织') }}<span v-if="isUsingDefaultRule">，</span>
              <template v-if="isUsingDefaultRule">
                <span class="user-count">{{ hasSelectedUsers.length }}</span> {{ $t('个用户') }}
              </template>
            </template>
              <template v-else>
                <span class="user-count">0</span>
              </template>
            </div>
            <bk-button theme="primary" text :disabled="!isShowSelectedText" @click="handleDeleteAll"> {{ $t('清空') }} </bk-button>
          </div>
          <div class="content">
            <div class="organization-content" v-if="isDepartSelectedEmpty">
              <div class="organization-item" v-for="item in hasSelectedDepartments" :key="item.id">
                <img class="folder-icon" src="./images/file-close.svg" alt="">
                <span class="organization-name" :title="item.name">{{ item.name }}</span>
                <img class="delete-depart-icon" src="./images/delete-fill.svg" alt="" @click="handleDelete(item, 'organization')">
              </div>
            </div>
            <div class="user-content" v-if="isUserSelectedEmpty">
              <div class="user-item" v-for="item in hasSelectedUsers" :key="item.id">
                <img :src="userDefaultAvatar" class="user-icon" alt="">
                <span class="user-name" :title="item.username !== '' ? `${item.display_name}(${item.username})` : item.display_name">
                  {{ item.display_name }}
                  <template v-if="item.username !== ''">
                    ({{ item.username }})
                  </template>
                </span>
                <img class="delete-icon" src="./images/delete-fill.svg" alt="" @click="handleDelete(item, 'user')">
              </div>
            </div>
            <div class="selected-empty-wrapper" v-if="isSelectedEmpty">
              <img src="./images/empty-display.svg" alt="" />
            </div>
          </div>
        </div>
      </div>
    </div>
    <div slot="footer">
      <bk-button
        theme="primary"
        :disabled="isDisabled"
        :loading="isConfirmLoading"
        @click="handleSave">
        {{ $t('确定') }}
      </bk-button>
      <bk-button
        style="margin-left: 10px;"
        @click="handleCancel">
        {{ $t('取消') }}
      </bk-button>
    </div>
  </bk-dialog>
</template>
<script>
import Tree from './tree';
import List from './list';
import { unique } from '@/common/tools';
import userDefaultAvatar from './images/personal-user.svg';
import request from './request';
import i18n from '@/language/i18n';

export default {
  name: '',
  components: {
    Tree,
    List,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    users: {
      type: Array,
      default: () => [],
    },
    departments: {
      type: Array,
      default: () => [],
    },
    title: {
      type: String,
      default: '选择用户或组织',
    },
    apiHost: {
      type: String,
      required: true,
    },
    defaultDepartment: {
      type: Array,
      default: () => [],
    },
    defaultUser: {
      type: Array,
      default: () => [],
    },
    isVerify: {
      type: Boolean,
      default: false,
    },
    customClose: {
      type: Boolean,
      default: false,
    },
    placeholder: {
      type: String,
      default: '用户或组织',
    },
    range: {
      type: String,
      default: 'all',
    },
  },
  data() {
    return {
      isLoading: false,
      isShowDialog: false,
      userDefaultAvatar,
      keyword: '',
      treeLoading: false,
      isBeingSearch: false,
      hasSelectedUsers: [],
      searchedUsers: [],
      searchedDepartment: [],
      hasSelectedDepartments: [],
      treeList: [],
      infiniteTreeKey: -1,
      searchedResult: [],
      // 搜索时 键盘上下键 hover 的 index
      focusItemIndex: -1,

      searchConditionList: [
        {
          id: 'fuzzy',
          name: i18n.t('模糊搜索'),
        },
        {
          id: 'exact',
          name: i18n.t('精确搜索'),
        },
      ],
      searchConditionValue: 'fuzzy',
      isConfirmLoading: false,
    };
  },
  computed: {
    isDisabled() {
      if (this.isLoading) {
        return true;
      }
      return this.hasSelectedUsers.length < 1 && this.hasSelectedDepartments.length < 1 && this.isVerify;
    },
    isHasSeachResult() {
      return (this.searchedDepartment.length > 0 || this.searchedUsers.length > 0) && !this.treeLoading;
    },
    isSeachResultEmpty() {
      return this.searchedDepartment.length < 1 && this.searchedUsers.length < 1 && !this.treeLoading;
    },
    isShowSelectedText() {
      return this.hasSelectedDepartments.length > 0 || this.hasSelectedUsers.length > 0;
    },
    isShowSearchResult() {
      return this.isBeingSearch && !this.treeLoading;
    },
    isShowMemberTree() {
      return !this.isBeingSearch && !this.treeLoading;
    },
    isDepartSelectedEmpty() {
      return this.hasSelectedDepartments.length > 0;
    },
    isUserSelectedEmpty() {
      return this.hasSelectedUsers.length > 0;
    },
    isSelectedEmpty() {
      return this.hasSelectedDepartments.length < 1 && this.hasSelectedUsers.length < 1;
    },
    style() {
      return {
        height: '383px',
      };
    },
    isUsingDefaultRule() {
      return this.range === 'all';
    },
  },
  watch: {
    show: {
      handler(value) {
        this.isShowDialog = !!value;
        if (this.isShowDialog) {
          this.infiniteTreeKey = new Date().getTime();
          const templateList = this.users.map(item => ({
            username: item.name,
            id: item.id,
            display_name: item.display_name,
            type: item.type,
          }));
          this.hasSelectedUsers.splice(0, this.hasSelectedUsers.length, ...templateList);
          this.hasSelectedDepartments.splice(0, this.hasSelectedDepartments.length, ...this.departments);
          this.fetchCategories(false, true);
          this.isConfirmLoading = false;
        }
      },
      immediate: true,
    },
    keyword(newVal, oldVal) {
      this.focusItemIndex = -1;
      if (!newVal && oldVal) {
        if (this.isBeingSearch) {
          this.infiniteTreeKey = new Date().getTime();
          this.fetchCategories(true, false);
          this.isBeingSearch = false;
        }
      }
    },
    apiHost: {
      handler(value) {
        this.userApi = `${value}/api/c/compapi/v2/usermanage/fe_list_department_profiles/`;
        this.departmentApi = `${value}/api/c/compapi/v2/usermanage/fe_list_departments/`;
        this.userSearchApi = `${value}/api/c/compapi/v2/usermanage/fe_list_users/`;
      },
      immediate: true,
    },
  },
  methods: {
    handleKeyup() {
      // 当搜索的结果数据小于10条时才支持键盘上下键选中
      if (!this.isBeingSearch || this.searchedResult.length > 10) {
        return;
      }
      const len = this.$refs.searchedResultsRef.renderData.length;
      this.focusItemIndex--;
      this.focusItemIndex = this.focusItemIndex < 0 ? -1 : this.focusItemIndex;
      if (this.focusItemIndex === -1) {
        this.focusItemIndex = len - 1;
      }
    },
    // 用户
    fetchUser(params = {}) {
      return request.getData(this.userApi, params);
    },
    // 组织
    fetchDepartment(params = {}) {
      return request.getData(this.departmentApi, params);
    },
    // 搜索用户
    fetchSearchUser(params = {}) {
      return request.getData(this.userSearchApi, params);
    },

    async fetchCategories(isTreeLoading = false, isDialogLoading = false) {
      this.isLoading = isDialogLoading;
      this.treeLoading = isTreeLoading;
      const params = {
        app_code: 'bk-magicbox',
        no_page: true,
        lookup_field: 'level',
        exact_lookups: 0,
      };
      try {
        const res = await this.fetchDepartment(params);
        const categories = [...res];
        categories.forEach((item) => {
          item.visiable = true;
          item.showRadio = true;
          item.expanded = false;
          item.disabled = false;
          // item.async = item.has_children
          item.async = true;
          item.loading = false;
          item.type = 'department';
          item.$id = `${item.id}&department`;

          if (this.hasSelectedDepartments.length > 0) {
            item.is_selected = this.hasSelectedDepartments.map(v => v.id).includes(item.id);
          } else {
            item.is_selected = false;
          }

          if (this.defaultDepartment.length > 0 && this.defaultDepartment.includes(item.id)) {
            item.is_selected = true;
          }
        });
        this.treeList.splice(0, this.treeList.length, ...categories);
      } catch (error) {
        console.error(error);
        throw new Error(error);
      } finally {
        this.treeLoading = false;
        this.isLoading = false;
      }
    },

    handleKeydown() {
      // 当搜索的结果数据小于10条时才支持键盘上下键选中
      if (!this.isBeingSearch || this.searchedResult.length > 10) {
        return;
      }
      const len = this.$refs.searchedResultsRef.renderData.length;
      this.focusItemIndex++;
      this.focusItemIndex = this.focusItemIndex > len - 1
        ? len
        : this.focusItemIndex;
      if (this.focusItemIndex === len) {
        this.focusItemIndex = 0;
      }
    },

    handleOnSelected(newVal, node) {
      if (newVal) {
        if (node.type === 'user') {
          this.hasSelectedUsers.push(node);
        } else {
          this.hasSelectedDepartments.push(node);
        }
      } else {
        if (node.type === 'user') {
          this.hasSelectedUsers = [...this.hasSelectedUsers.filter(item => item.id !== node.id)];
        } else {
          this.hasSelectedDepartments = [...this.hasSelectedDepartments.filter(item => item.id !== node.id)];
        }
      }
    },

    handleDeleteAll() {
      if (this.searchedUsers.length) {
        this.searchedUsers.forEach((search) => {
          search.is_selected = false;
        });
      }
      if (this.searchedDepartment.length) {
        this.searchedDepartment.forEach((organ) => {
          organ.is_selected = false;
        });
      }
      this.hasSelectedUsers.splice(0, this.hasSelectedUsers.length, ...[]);
      this.hasSelectedDepartments.splice(0, this.hasSelectedDepartments.length, ...[]);
      this.$refs.userTreeRef && this.$refs.userTreeRef.clearAllIsSelectedStatus();
    },

    handleConditionSelcted() {
      this.handleSearch();
    },

    async handleSearch() {
      if (this.keyword === '' || this.treeLoading) {
        return;
      }

      if (this.focusItemIndex !== -1) {
        this.$refs.searchedResultsRef.setCheckStatusByIndex();
        return;
      }

      this.treeList.splice(0, this.treeList.length, ...[]);
      this.isBeingSearch = true;
      this.treeLoading = true;
      this.searchedResult.splice(0, this.searchedResult.length, ...[]);
      this.searchedDepartment.splice(0, this.searchedDepartment.length, ...[]);
      this.searchedUsers.splice(0, this.searchedUsers.length, ...[]);
      const departIds = [...this.hasSelectedDepartments.map(item => item.id)];
      const userIds = [...this.hasSelectedUsers.map(item => item.id)];
      const params = {
        app_code: 'bk-magicbox',
        no_page: true,
      };
      const requestDepartParams = {
        ...params,
        lookup_field: 'name',
      };
      const requestUserParams = {
        ...params,
        lookup_field: 'username',
      };

      if (this.searchConditionValue === 'exact') {
        requestDepartParams.exact_lookups = this.keyword;
        requestUserParams.exact_lookups = this.keyword;
      } else {
        requestDepartParams.fuzzy_lookups = this.keyword;
        requestUserParams.fuzzy_lookups = this.keyword;
      }

      try {
        // 组织
        const fetchList = [this.fetchDepartment(requestDepartParams)];
        if (this.isUsingDefaultRule) { // 用户
          fetchList.push(this.fetchSearchUser(requestUserParams));
        }
        const res = await Promise.all(fetchList);
        const departments = unique(res[0], 'id');
        const users = unique(res[1], 'id');
        departments.forEach((depart) => {
          depart.showRadio = true;
          depart.type = 'department';
          depart.$id = `${depart.id}&department`;
          if (departIds.length && departIds.includes(depart.id)) {
            this.$set(depart, 'is_selected', true);
          } else {
            this.$set(depart, 'is_selected', false);
          }
          if (this.defaultDepartment.length && this.defaultDepartment.includes(depart.id)) {
            this.$set(depart, 'is_selected', true);
            this.$set(depart, 'disabled', false);
          }
        });
        this.searchedDepartment.splice(0, this.searchedDepartment.length, ...departments);
        users.forEach((user) => {
          user.showRadio = true;
          user.type = 'user';
          user.$id = `${user.id}&user`;
          if (userIds.length && userIds.includes(user.id)) {
            this.$set(user, 'is_selected', true);
          } else {
            this.$set(user, 'is_selected', false);
          }
          if (this.defaultUser.length && this.defaultUser.includes(user.id)) {
            this.$set(user, 'is_selected', true);
            this.$set(user, 'disabled', false);
          }
        });
        this.searchedUsers.splice(0, this.searchedUsers.length, ...users);
        this.searchedResult.splice(0, this.searchedResult.length, ...this.searchedDepartment.concat(this.searchedUsers));
      } catch (error) {
        console.error(error);
        throw new Error(error);
      } finally {
        this.treeLoading = false;
      }
    },

    async handleRemoteLoadNode(payload) {
      payload.loading = true;
      const params = {
        app_code: 'bk-magicbox',
        no_page: true,
      };
      const requestDepartParams = {
        ...params,
        lookup_field: 'parent',
        exact_lookups: payload.id,
      };
      const requestUserParams = {
        ...params,
        lookup_value: payload.id,
      };

      try {
        // 组织
        const fetchList = [this.fetchDepartment(requestDepartParams)];
        if (this.isUsingDefaultRule) { // 用户
          fetchList.push(this.fetchUser(requestUserParams));
        }
        const res = await Promise.all(fetchList);
        const categories = unique(res[0], 'id');
        const members = unique(res[1], 'id');
        const curIndex = this.treeList.findIndex(item => item.id === payload.id);
        if (curIndex === -1) {
          return;
        }
        const treeList = [];
        treeList.splice(0, 0, ...this.treeList);
        categories.forEach((child, childIndex) => {
          child.visiable = true;
          child.loading = false;
          child.showRadio = true;
          child.expanded = false;
          child.disabled = false;
          child.showCount = true;
          child.async = child.has_children;
          child.type = 'department';
          child.$id = `${child.id}&department`;

          if (this.hasSelectedDepartments.length > 0) {
            child.is_selected = this.hasSelectedDepartments.map(item => item.id).includes(child.id);
          } else {
            child.is_selected = false;
          }

          if (this.defaultDepartment.length > 0 && this.defaultDepartment.includes(child.id)) {
            child.is_selected = true;
            child.disabled = false;
          }
        });

        members.forEach((child) => {
          child.visiable = payload.expanded;
          child.level = payload.level + 1;
          child.loading = false;
          child.showRadio = true;
          child.expanded = false;
          child.disabled = false;
          child.type = 'user';
          child.async = false;
          child.parent = payload.id;
          child.$id = `${child.id}&user`;

          if (this.hasSelectedUsers.length > 0) {
            child.is_selected = this.hasSelectedUsers.map(item => item.id).includes(child.id);
          } else {
            child.is_selected = false;
          }
          const existSelectedNode = this.treeList.find(item => item.is_selected && item.id === child.id && item.type === 'user');
          if (existSelectedNode) {
            child.is_selected = true;
            child.disabled = true;
          }

          if (this.defaultUser.length && this.defaultUser.includes(child.id)) {
            child.is_selected = true;
            child.disabled = false;
          }
        });

        const loadChildren = categories.concat(members);
        treeList.splice(curIndex + 1, 0, ...loadChildren);
        this.treeList.splice(0, this.treeList.length, ...treeList);
        if (!payload.children) {
          payload.children = [];
        }
        payload.children.splice(0, payload.children.length, ...loadChildren);
      } catch (error) {
        console.error(error);
        throw new Error(error);
      } finally {
        setTimeout(() => {
          payload.loading = false;
        }, 300);
      }
    },

    handleDelete(item, type) {
      if (this.isBeingSearch) {
        if (this.searchedUsers.length) {
          this.searchedUsers.forEach((search) => {
            if (search.id === item.id) {
              search.is_selected = false;
            }
          });
        }
        if (this.searchedDepartment.length) {
          this.searchedDepartment.forEach((organ) => {
            if (organ.id === item.id) {
              organ.is_selected = false;
            }
          });
        }
      } else {
        this.$refs.userTreeRef.setSingleSelectedStatus(item.id, false);
      }
      if (type === 'user') {
        this.hasSelectedUsers = [...this.hasSelectedUsers.filter(user => user.id !== item.id)];
      } else {
        this.hasSelectedDepartments = [...this.hasSelectedDepartments.filter(organ => organ.id !== item.id)];
      }
    },

    async handleSearchResultSelected(newVal, oldVal, localVal, item) {
      if (item.type === 'user') {
        this.handleSearchUserSelected(newVal, item);
      } else {
        if (newVal) {
          this.hasSelectedDepartments.push(item);
        } else {
          this.hasSelectedDepartments = this.hasSelectedDepartments.filter(organ => organ.id !== item.id);
        }
      }
    },

    handleSearchUserSelected(newVal, item) {
      if (newVal) {
        this.hasSelectedUsers.push(item);
      } else {
        this.hasSelectedUsers = this.hasSelectedUsers.filter(user => user.id !== item.id);
      }
    },

    handleAfterLeave() {
      this.keyword = '';
      this.treeLoading = false;
      this.isBeingSearch = false;
      this.hasSelectedUsers.splice(0, this.hasSelectedUsers.length, ...[]);
      this.hasSelectedDepartments.splice(0, this.hasSelectedDepartments.length, ...[]);
      this.searchedDepartment.splice(0, this.searchedDepartment.length, ...[]);
      this.searchedUsers.splice(0, this.searchedUsers.length, ...[]);
      this.searchedResult.splice(0, this.searchedResult.length, ...[]);
      this.treeList.splice(0, this.treeList.length, ...[]);
      this.focusItemIndex = -1;
      this.$refs.userTreeRef && this.$refs.userTreeRef.clearAllIsSelectedStatus();
      this.searchConditionValue = 'fuzzy';
      this.$emit('update:show', false);
      this.$emit('on-after-leave');
    },

    handleCancel() {
      this.$emit('update:show', false);
      this.$emit('cancel');
    },

    handleSave() {
      const tempList = [];
      this.hasSelectedUsers.forEach((item) => {
        tempList.push({
          name: item.username,
          display_name: item.display_name,
          id: item.id,
          type: 'user',
        });
      });

      this.hasSelectedDepartments.forEach((item) => {
        tempList.push({
          name: item.name,
          id: item.id,
          type: 'department',
        });
      });
      if (!this.customClose) {
        this.$emit('update:show', false);
      } else {
        // 外界控制关闭弹窗时机
        this.isConfirmLoading = true;
      }
      console.warn(tempList);
      this.$emit('sumbit', tempList);
    },
  },
};
</script>
<style lang='scss'>
    @import './index.scss';
</style>
