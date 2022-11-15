<template>
  <div
    ref="searchWrapper"
    v-clickoutside="hideFilterList"
    class="bk-searcher-wrapper"
  >
    <div
      v-if="!searchParams.length && !fixedSearchParams.length && !showFilter"
      class="placeholder"
      @click="foucusSearcher($event)"
    >
      {{ $t('搜索，支持上下键选择，按Enter选中') }}
    </div>
    <div
      class="bk-searcher"
      @click="foucusSearcher($event)"
    >
      <ul
        ref="searchParamsWrapper"
        class="search-params-wrapper"
      >
        <li
          v-for="(fsp, fspIndex) in fixedSearchParams"
          v-if="fixedSearchParams && fixedSearchParams.length"
          :key="fspIndex"
        >
          <div
            class="selectable"
            @click.stop="fixedSearchParamsClickHandler($event, fsp, fspIndex)"
          >
            <div class="name">
              {{ fsp.text }}
            </div>
            <div
              v-if="fsp.value"
              class="value-container"
            >
              <div class="value">
                {{ fsp.value.text }}
              </div>
            </div>
          </div>
        </li>
        <li
          v-for="(sp, spIndex) in searchParams"
          v-if="searchParams && searchParams.length"
          :key="spIndex"
        >
          <div
            class="selectable"
            @click.stop="searchParamsClickHandler($event, sp, spIndex)"
          >
            <div class="name">
              {{ sp.text }}
            </div>
            <div
              v-if="sp.value"
              class="value-container"
            >
              <div class="value">
                {{ sp.value.text }}
              </div>
              <div
                class="remove-search-params"
                @click.stop="removeSearchParams($event, sp, spIndex)"
              >
                <i class="paasng-icon paasng-close" />
              </div>
            </div>
          </div>
        </li>
        <li ref="searchInputParent">
          <input
            ref="searchInput"
            v-model="curInputValue"
            type="text"
            class="input"
            :style="{ width: `${maxInputWidth}px`, minWidth: `${minInputWidth}px` }"
            :maxlength="inputSearchKey || showFilterValue ? Infinity : 0"
            @keyup="inputKeyup($event)"
            @keypress="keyboardEvt($event)"
            @keydown="keyboardEvt($event)"
          >
        </li>
      </ul>
    </div>
    <div
      v-show="showFilter && filterList.length"
      class="bk-searcher-dropdown-menu filter-list"
    >
      <div
        class="bk-searcher-dropdown-content"
        :class="showFilter ? 'is-show' : ''"
        :style="{ left: `${searcherDropdownLeft}px` }"
      >
        <ul
          v-bkloading="{ isLoading: filterValueLoading }"
          class="bk-searcher-dropdown-list"
        >
          <li
            v-for="(filter, filterIndex) in filterList"
            :key="filterIndex"
          >
            <a
              href="javascript:void(0);"
              :class="filterIndex === filterKeyboardIndex ? 'active' : ''"
              @click="selectFilter(filter, filterIndex)"
            >{{ filter.text }}</a>
          </li>
        </ul>
      </div>
    </div>

    <div
      v-show="showFilterValue && filterValueList.length"
      class="bk-searcher-dropdown-menu filter-value-list"
    >
      <div
        ref="filterValueListNode"
        class="bk-searcher-dropdown-content"
        :class="showFilterValue ? 'is-show' : ''"
        :style="{ left: `${searcherDropdownLeft}px` }"
      >
        <ul
          v-if="filterValueList && filterValueList.length"
          class="bk-searcher-dropdown-list"
        >
          <li
            v-for="(fv, fvIndex) in filterValueList"
            :key="fvIndex"
          >
            <a
              href="javascript:void(0);"
              :class="fvIndex === filterValueKeyboardIndex ? 'active' : ''"
              @click="selectFilterValue(fv)"
            >{{ fv.text }}</a>
          </li>
        </ul>
        <ul
          v-else
          class="bk-searcher-dropdown-list"
        >
          <li>
            <a href="javascript:void(0);"> {{ $t('没有数据') }} </a>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
    import clickoutside from './clickoutside';

    /**
     * 获取元素相对于页面的高度
     *
     * @param node {Object} 指定的 DOM 元素
     *
     * @return {number} 值
     */
    // function getActualTop (node) {
    //     let actualTop = node.offsetTop;
    //     let current = node.offsetParent;

    //     while (current !== null) {
    //         actualTop += current.offsetTop;
    //         current = current.offsetParent;
    //     }

    //     return actualTop;
    // }

    /**
     * 获取元素相对于页面左侧的宽度
     *
     * @param node {Object} 指定的 DOM 元素
     *
     * @return {number} 值
     */
    function getActualLeft (node) {
        let actualLeft = node.offsetLeft;
        let current = node.offsetParent;

        while (current !== null) {
            actualLeft += current.offsetLeft;
            current = current.offsetParent;
        }

        return actualLeft;
    }

    /**
     * 获取字符串长度，中文算两个，英文算一个
     *
     * @param {string} str 字符串
     *
     * @return {number} 结果
     */
    function getStringLen (str) {
        let len = 0;
        for (let i = 0; i < str.length; i++) {
            if (str.charCodeAt(i) > 127 || str.charCodeAt(i) === 94) {
                len += 2;
            } else {
                len++;
            }
        }
        return len;
    }

    /**
     * 在当前节点后面插入节点
     *
     * @param {Object} newElement 待插入 dom 节点
     * @param {Object} targetElement 当前节点
     */
    function insertAfter (newElement, targetElement) {
        const parent = targetElement.parentNode;
        if (parent.lastChild === targetElement) {
            parent.appendChild(newElement);
        } else {
            parent.insertBefore(newElement, targetElement.nextSibling);
        }
    }

    export default {
        directives: {
            clickoutside
        },
        props: {
            // 固定的搜索参数
            fixedSearchParams: {
                type: Array,
                default () {
                    return [];
                }
            },
            // 过滤项下拉框列表
            filterList: {
                type: Array,
                default () {
                    return [];
                }
            },
            // 在文本框中输入任意关键字搜索，如果为空，那么说明不支持在文本框中输入任意关键字搜索
            inputSearchKey: {
                type: String,
                default: 'search'
            },
            // 输入框的最小宽度
            minInputWidth: {
                type: Number,
                default: 10
            }
        },
        data () {
            return {
                curInputValue: '',

                // 搜索参数
                searchParams: [],
                // 固定的搜索参数的 id
                fixedSearchParamsIds: [],
                // filterList 的缓存
                filterListCache: [],
                // 标识是由哪个 filter 弹出的 filter value 弹层
                filterValueKey: '',
                // 选中一个 filter 后，filter 的可选值集合
                filterValueList: [],
                // filterValueList 的缓存，搜索使用
                filterValueListCache: [],
                // filterValue 键盘上下的索引
                filterValueKeyboardIndex: -1,
                filterKeyboardIndex: -1,
                // 渲染 filter 的可选值集合的 loading
                filterValueLoading: false,
                // 是否显示 filter 的可选值集合
                showFilterValue: false,
                // 是否显示过滤项
                showFilter: false,
                // search-params-wrapper 里的 li 元素的 margin 值
                searchParamsItemMargin: 0,
                // 过滤项下拉框的左偏移
                searcherDropdownLeft: 0
            };
        },
        computed: {
            maxInputWidth () {
                return this.curInputValue.length * 10;
            }
        },
        watch: {
            curInputValue (val) {
                const filterValueList = [];
                this.filterValueListCache.forEach(item => {
                    if (item.text.indexOf(val) >= 0) {
                        filterValueList.push(JSON.parse(JSON.stringify(item)));
                    }
                });
                this.filterValueList.splice(0, this.filterValueList.length, ...filterValueList);
                this.filterValueKeyboardIndex = -1;
                this.filterKeyboardIndex = -1;
            },
            showFilterValue (val) {
                if (val) {
                    const filterValueListNode = this.$refs.filterValueListNode;
                    filterValueListNode && filterValueListNode.scrollTo(0, 0);
                }
            }
        },
        mounted () {
            const fixedSearchParams = [];
            const fixedSearchParamsIds = [];
            this.fixedSearchParams.forEach(fsp => {
                let selected = fsp.list.filter(val => val.isSelected)[0];
                if (!selected) {
                    selected = fsp.list[0];
                }
                fsp.value = selected;
                fixedSearchParams.push(JSON.parse(JSON.stringify(fsp)));
                fixedSearchParamsIds.push(fsp.id);
            });
            this.fixedSearchParams.splice(0, this.fixedSearchParams.length, ...fixedSearchParams);
            this.fixedSearchParamsIds.splice(0, this.fixedSearchParamsIds.length, ...fixedSearchParamsIds);

            const filterList = [];
            const searchParams = [];
            this.filterList.forEach(filter => {
                if (filter.list) {
                    const selected = filter.list.filter(val => val.isSelected)[0];
                    if (selected) {
                        filter.value = selected;
                        this.filterValueKey = filter.id;
                        searchParams.push(JSON.parse(JSON.stringify(filter)));
                    } else {
                        filterList.push(JSON.parse(JSON.stringify(filter)));
                    }
                } else {
                    filterList.push(JSON.parse(JSON.stringify(filter)));
                }
            });
            filterList.sort((a, b) => a.id < b.id ? 1 : -1);

            this.searchParams.splice(0, this.searchParams.length, ...searchParams);
            this.filterList.splice(0, this.filterList.length, ...filterList);
            this.filterListCache.splice(0, this.filterListCache.length, ...filterList);

            const { searchWrapper, searchParamsWrapper } = this.$refs;
            this.searcherDropdownLeft = getActualLeft(searchParamsWrapper) - getActualLeft(searchWrapper) +
                this.searchParamsItemMargin;

            // 绑定清除 searchParams 的方法，父组件调用方式如下：
            // this.$refs.bkSearcher.$emit('resetSearchParams')
            this.$on('resetSearchParams', isEmitSearch => {
                this.searchParams.splice(0, this.searchParams.length, ...[]);
                // 需要重新触发 search
                if (isEmitSearch) {
                    this.$emit('search', this.fixedSearchParams);
                }
            });
        },
        methods: {
            /**
             * filter 选择事件回调
             *
             * @param {Object} filter 当前选择的 filter
             * @param {number} filterIndex 当前选择的 filter 的索引
             */
            selectFilter (filter, filterIndex) {
                // 当前 filter 有可用的值
                this.filterKeyboardIndex = -1;
                if (filter.list && !filter.dynamicData) {
                    this.filterValueLoading = true;
                    const searchParams = [];
                    searchParams.splice(0, 0, ...this.searchParams);
                    searchParams.push(filter);
                    this.searchParams.splice(0, this.searchParams.length, ...searchParams);

                    // 一个字符大约是 8 px，横向 padding 10 px，左右 padding 一共是 20 px
                    this.searcherDropdownLeft += getStringLen(filter.text) * 8 + 10;
                    setTimeout(() => {
                        this.$refs.searchInput.focus();
                        this.filterValueKey = filter.id;
                        this.filterValueList.splice(0, this.filterValueList.length, ...filter.list);
                        this.filterValueListCache.splice(0, this.filterValueListCache.length, ...filter.list);
                        this.filterValueLoading = false;
                        this.showFilter = false;
                        this.showFilterValue = true;
                    }, 300);
                } else {
                    this.filterValueLoading = true;
                    const searchParams = [];
                    searchParams.splice(0, 0, ...this.searchParams);
                    searchParams.push(filter);
                    this.searchParams.splice(0, this.searchParams.length, ...searchParams);

                    this.searcherDropdownLeft += getStringLen(filter.text) * 8 + 10;

                    new Promise((resolve, reject) => {
                        const fixedSearchParams = {};
                        this.fixedSearchParams.forEach(fsp => {
                            fixedSearchParams[fsp.id] = fsp.value.id;
                        });
                        this.$emit('getFilterListData', filter, fixedSearchParams, resolve, reject);
                    }).then(data => {
                        filter.list = data;
                        // 标识 filter list 数据是根据请求异步获取的，不是一开始就设置好的
                        // 用这个属性来控制，每次都从后端获取数据
                        filter.dynamicData = true;
                        filter = JSON.parse(JSON.stringify(filter));
                        setTimeout(() => {
                            this.$refs.searchInput.focus();
                            this.filterValueKey = filter.id;
                            this.filterValueList.splice(0, this.filterValueList.length, ...filter.list);
                            this.filterValueListCache.splice(0, this.filterValueListCache.length, ...filter.list);
                            this.filterValueLoading = false;
                            this.showFilter = false;
                            this.showFilterValue = true;
                        }, 200);
                    }, err => {
                        console.error(err);
                    });
                }
            },

            /**
             * filter value 选择事件回调
             *
             * @param {Object} fv 当前选择的 fv
             */
            selectFilterValue (fv, isFromKeyboard) {
                const filterValueList = [];
                this.filterValueList.forEach(item => {
                    item.isSelected = item.id === fv.id;
                    filterValueList.push(JSON.parse(JSON.stringify(item)));
                });
                this.filterValueList.splice(0, this.filterValueList.length, ...filterValueList);

                const selected = this.filterValueList.filter(val => val.isSelected)[0];

                // 说明选择的是固定参数的 fixedSearchParams
                if (this.fixedSearchParamsIds.indexOf(this.filterValueKey) > -1) {
                    const fixedSearchParams = [];
                    this.fixedSearchParams.forEach(fsp => {
                        if (fsp.id === this.filterValueKey) {
                            fsp.value = selected;
                        }
                        fixedSearchParams.push(JSON.parse(JSON.stringify(fsp)));
                    });
                    this.fixedSearchParams.splice(0, this.fixedSearchParams.length, ...fixedSearchParams);
                } else {
                    // const curFilter = this.filterList.filter(item => item.id === this.filterValueKey)[0];
                    const searchParams = [];
                    this.searchParams.forEach(sp => {
                        if (sp.id === this.filterValueKey) {
                            sp.value = selected;
                        }
                        searchParams.push(JSON.parse(JSON.stringify(sp)));
                    });
                    this.searchParams.splice(0, this.searchParams.length, ...searchParams);

                    // 更新 filterList，把选择的删除掉
                    const filterList = [];
                    this.filterList.forEach(item => {
                        if (item.id !== this.filterValueKey) {
                            filterList.push(JSON.parse(JSON.stringify(item)));
                        }
                    });
                    filterList.sort((a, b) => a.id < b.id ? 1 : -1);
                    this.filterList.splice(0, this.filterList.length, ...filterList);
                }

                if (isFromKeyboard) {
                    this.showNexfFilter();
                } else {
                    this.hideFilterList();
                }
                this.$emit('search', this.fixedSearchParams.concat(this.searchParams));
            },

            /**
             * 固定的搜索参数 点击事件
             *
             * @param {Object} fsp 当前点击的固定参数对象
             * @param {number} fspIndex 当前点击的固定参数对象 索引
             */
            fixedSearchParamsClickHandler (e, fsp, fspIndex) {
                this.hideFilterList();

                const target = e.currentTarget;

                const nameNode = target.querySelector('.name');
                const valueContainerNode = target.querySelector('.value-container');

                const { searchWrapper, searchParamsWrapper } = this.$refs;
                // this.searcherDropdownLeft = getActualLeft(target) - getActualLeft(searchWrapper)
                //     + this.searchParamsItemMargin + getActualLeft(valueContainerNode) - getActualLeft(nameNode)
                this.searcherDropdownLeft = getActualLeft(searchParamsWrapper) - getActualLeft(searchWrapper) +
                    this.searchParamsItemMargin + getActualLeft(valueContainerNode) - getActualLeft(nameNode);

                this.showFilter = false;
                this.showFilterValue = true;
                this.filterValueKey = fsp.id;
                this.filterValueList.splice(0, this.filterValueList.length, ...fsp.list);
                this.filterValueListCache.splice(0, this.filterValueListCache.length, ...fsp.list);

                insertAfter(this.$refs.searchInputParent, target.parentNode);
                this.$nextTick(() => {
                    this.$refs.searchInput.focus();
                });
            },

            /**
             * 搜索参数 点击事件
             *
             * @param {Object} e 事件对象
             * @param {Object} sp 当前点击的固定参数对象
             * @param {number} spIndex 当前点击的固定参数对象 索引
             */
            searchParamsClickHandler (e, sp, spIndex) {
                this.hideFilterList();

                const target = e.currentTarget;
                const nameNode = target.querySelector('.name');
                const valueContainerNode = target.querySelector('.value-container');

                const { searchWrapper } = this.$refs;
                this.searcherDropdownLeft = getActualLeft(target) - getActualLeft(searchWrapper) +
                    this.searchParamsItemMargin + getActualLeft(valueContainerNode) - getActualLeft(nameNode);

                this.showFilter = false;
                this.showFilterValue = true;
                this.filterValueKey = sp.id;
                this.filterValueList.splice(0, this.filterValueList.length, ...sp.list);
                this.filterValueListCache.splice(0, this.filterValueListCache.length, ...sp.list);

                insertAfter(this.$refs.searchInputParent, target.parentNode);
                this.$nextTick(() => {
                    this.$refs.searchInput.focus();
                });
            },

            /**
             * 组件 click 事件
             */
            foucusSearcher (e) {
                this.$nextTick(() => {
                    this.$refs.searchInput.focus();
                });

                if (this.showFilterValue) {
                    return;
                }

                const { searchParamsWrapper, searchInput } = this.$refs;
                let searcherDropdownLeft = searchInput.offsetParent.offsetLeft + this.searchParamsItemMargin * 2;
                const offsetWidth = parseInt(searchParamsWrapper.offsetWidth, 10);
                if (searcherDropdownLeft > offsetWidth - this.minInputWidth * 2) {
                    searcherDropdownLeft = offsetWidth - this.minInputWidth * 3 / 2 + this.searchParamsItemMargin * 2;
                }
                this.searcherDropdownLeft = searcherDropdownLeft;

                this.showFilterValue = false;
                this.showFilter = true;
            },

            /**
             * 删除当前点击的这个 param
             *
             * @param {Object} e 事件对象
             * @param {Object} sp 当前点击的固定参数对象
             * @param {number} spIndex 当前点击的固定参数对象 索引
             */
            removeSearchParams (e, sp, spIndex) {
                const searchParams = [];
                this.searchParams.forEach(s => {
                    if (s.id !== sp.id) {
                        searchParams.push(JSON.parse(JSON.stringify(s)));
                    }
                });
                this.searchParams.splice(0, this.searchParams.length, ...searchParams);

                // 更新 filterList，把当前点击的删掉
                const filterList = [];
                this.filterList.forEach(item => {
                    filterList.push(JSON.parse(JSON.stringify(item)));
                });
                if (sp.value) {
                    delete sp.value;
                    filterList.push(JSON.parse(JSON.stringify(sp)));
                }
                const item = filterList.filter(item => {
                    return sp.id === item.id;
                });
                if (!item.length) {
                    filterList.push(JSON.parse(JSON.stringify(sp)));
                }
                filterList.sort((a, b) => a.id < b.id ? 1 : -1);
                this.filterList.splice(0, this.filterList.length, ...filterList);
                this.hideFilterList();

                this.$emit('search', this.fixedSearchParams.concat(this.searchParams));
            },

            /**
             * 删除所有选项
             */
            removeAllParams () {
                this.$nextTick(() => {
                    this.searchParams.forEach((item, index) => {
                        this.removeSearchParams({}, item, index);
                    });
                    this.searchParams = [];
                });
            },

            /**
             * 隐藏 filterList 和 filterValueList 的弹层
             */
            hideFilterList () {
                this.showFilter = false;
                this.showFilterValue = false;
                this.curInputValue = '';
                this.filterValueKeyboardIndex = -1;
                this.filterKeyboardIndex = -1;
                this.filterValueKey = '';
                this.filterValueList.splice(0, this.filterValueList.length, ...[]);
                this.filterValueListCache.splice(0, this.filterValueListCache.length, ...[]);
                this.$nextTick(() => {
                    this.$refs.searchInput.blur();
                });
                // 关闭 filter 和 filter value 时，如果发现 searchParams 里有 不存在 value 的
                // 说明是还未选择 filter value 的情况，这时候要清除掉
                const searchParams = [];
                this.searchParams.forEach(sp => {
                    if (sp.value) {
                        searchParams.push(JSON.parse(JSON.stringify(sp)));
                    }
                });
                this.searchParams.splice(0, this.searchParams.length, ...searchParams);

                insertAfter(this.$refs.searchInputParent, this.$refs.searchParamsWrapper.lastChild);
            },

            /**
             * 展示下一个filterItem
             */
            showNexfFilter () {
                this.hideFilterList();
                this.$nextTick(() => {
                    this.foucusSearcher();
                });
            },

            /*
             * 清除最近一个选项
             */
            clearSearchParams () {
                if (this.searchParams.length) {
                    const lastIndex = this.searchParams.length - 1;
                    const curParams = this.searchParams[lastIndex];
                    this.removeSearchParams({}, curParams, lastIndex);
                    setTimeout(() => {
                        this.foucusSearcher();
                    }, 300);
                }
            },
            /**
             * 输入框 keyup 事件
             *
             * @param {Object} e 事件对象
             */
            inputKeyup (e) {
                if (!this.showFilterValue) {
                    if (this.filterList.length) {
                        switch (e.keyCode) {
                            // down
                            case 40:
                                if (this.filterKeyboardIndex < this.filterList.length - 1) {
                                    this.filterKeyboardIndex++;
                                }
                                break;
                            // up
                            case 38:
                                if (this.filterKeyboardIndex > 0) {
                                    this.filterKeyboardIndex--;
                                }
                                break;
                            // enter
                            case 13:
                                const filterItem = this.filterList[this.filterKeyboardIndex];
                                filterItem && this.selectFilter(filterItem, this.filterKeyboardIndex);
                                break;
                            // Backspace
                            case 8:
                                if (!this.curInputValue) {
                                    this.clearSearchParams();
                                }
                                break;
                            default:
                        }
                    }
                    return;
                }
                const { filterValueListNode } = this.$refs;
                // 最大高度 320，每个 item 高度 42

                switch (e.keyCode) {
                    // down
                    case 40:
                        if (this.filterValueKeyboardIndex < this.filterValueList.length - 1) {
                            this.filterValueKeyboardIndex++;
                            if (this.filterValueKeyboardIndex >= 8) {
                                filterValueListNode.scrollTo(0, filterValueListNode.scrollTop + 45);
                            }
                        }
                        break;
                    // up
                    case 38:
                        if (this.filterValueKeyboardIndex > 0) {
                            this.filterValueKeyboardIndex--;
                            if (this.filterValueKeyboardIndex < Math.ceil((filterValueListNode.scrollHeight - 320) / 42)) {
                                filterValueListNode.scrollTo(0, filterValueListNode.scrollTop - 42);
                            }
                        }
                        break;
                    // enter
                    case 13:
                        const filterValueItem = this.filterValueList[this.filterValueKeyboardIndex];
                        filterValueItem && this.selectFilterValue(filterValueItem, true);
                        break;
                    // Backspace
                    case 8:
                        if (!this.curInputValue) {
                            this.clearSearchParams();
                        }
                        break;
                    default:
                }
            },

            /**
             * 阻止 input 框一些按键的默认事件
             *
             * @param {Object} e 事件对象
             */
            keyboardEvt (e) {
                switch (e.code) {
                    // down
                    case 'ArrowDown':
                        e.stopPropagation();
                        e.preventDefault();
                        break;
                    // up
                    case 'ArrowUp':
                        e.stopPropagation();
                        e.preventDefault();
                        break;
                    // left
                    case 'ArrowLeft':
                        e.stopPropagation();
                        e.preventDefault();
                        break;
                    // right
                    case 'ArrowRight':
                        e.stopPropagation();
                        e.preventDefault();
                        break;
                    default:
                }
            }
        }
    };
</script>

<style lang="scss" scoped>
    @import './index.scss';
</style>
