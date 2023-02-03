import i18n from '@/language/i18n';

/**
 * 对应titleValue
 */
const titleConfig = {
  'ql-bold': i18n.t('加粗'),
  'ql-color': i18n.t('颜色'),
  'ql-font': i18n.t('字体'),
  'ql-code': i18n.t('插入代码'),
  'ql-italic': i18n.t('斜体'),
  'ql-link': i18n.t('添加链接'),
  'ql-background': i18n.t('背景颜色'),
  'ql-size': i18n.t('字体大小'),
  'ql-strike': i18n.t('删除线'),
  'ql-script': i18n.t('上标/下标'),
  'ql-underline': i18n.t('下划线'),
  'ql-blockquote': i18n.t('引用'),
  'ql-header': i18n.t('标题'),
  'ql-indent': i18n.t('缩进'),
  'ql-list': i18n.t('列表'),
  'ql-align': i18n.t('文本对齐'),
  'ql-direction': i18n.t('文本方向'),
  'ql-code-block': i18n.t('代码块'),
  'ql-formula': i18n.t('公式'),
  'ql-image': i18n.t('图片'),
  'ql-video': i18n.t('视频'),
  'ql-clean': i18n.t('清除字体样式')
};

/**
 * 富文本title提示
 */
export function addQuillTitle () {
  const oToolBar = document.querySelector('.ql-toolbar');
  const aButton = oToolBar.querySelectorAll('.ql-formats>button');
  const aSelect = oToolBar.querySelectorAll('.ql-formats>select');
  const aSpan = oToolBar.querySelectorAll('.ql-formats>span.ql-picker');
  aButton.forEach(function (item) {
    if (item.className === 'ql-script') {
      item.value === 'sub' ? item.title = i18n.t('下标') : item.title = i18n.t('上标');
    } else if (item.className === 'ql-indent') {
      item.value === '+1' ? item.title = i18n.t('向右缩进') : item.title = i18n.t('向左缩进');
    } else {
      item.title = titleConfig[item.classList[0]];
    }
  });
  aSpan.forEach(function (item) {
    item.title = titleConfig[item.classList[0]];
  });
  aSelect.forEach(function (item) {
    item.parentNode.title = titleConfig[item.classList[0]];
  });
}
