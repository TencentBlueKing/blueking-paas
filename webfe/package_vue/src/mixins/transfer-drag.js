export default {
  data() {
    return {
      mixinTargetBuildpackIds: null,
    };
  },
  methods: {
    /**
     * 开启拖拽功能
     * @param {*} className
     */
    mixinSetDraggableProp(className) {
      const itemElements = document.querySelectorAll(className);
      for (let i = 0; i < itemElements.length; i++) {
        itemElements[i].draggable = true;
      }
    },

    /**
     * 拖拽事件绑定
     * @param {*} listEl 需要绑定拖拽的元素列表
     * @param {*} listClassName
     */
    mixinBindDragEvent(listEl, listClassName) {
      if (!listEl) {
        return;
      }

      // 当前拖拽元素
      let sourceNode = null;

      // 拖拽开始
      listEl.ondragstart = (e) => {
        setTimeout(() => {
          e.target.classList.add('moving');
        }, 0);
        if (e.target.getAttribute('data-id')) {
          sourceNode = e.target.parentNode;
        }
        sourceNode = e.target;
        if (e.dataTransfer) {
          e.dataTransfer.effectAllowed = 'move';
        }
      };

      // 移入到某个元素上
      listEl.ondragenter = (e) => {
        // 未改变
        if (targetNode === sourceNode) {
          return;
        }
        let targetNode = e.target;
        if (e.target.getAttribute('data-id')) {
          targetNode = e.target.parentNode;
        }
        const children = Array.from(listEl.children);
        const sourceIndex = children.indexOf(sourceNode);
        const targetIndex = children.indexOf(targetNode);
        if (sourceIndex < targetIndex) { // 向下
          listEl.insertBefore(sourceNode, targetNode?.nextElementSiBling);
        } else { // 向上
          listEl.insertBefore(sourceNode, targetNode);
        }
      };

      listEl.ondragover = (e) => {
        e.preventDefault();
      };

      // 结束拖拽
      listEl.ondragend = (e) => {
        e.preventDefault();
        e.target.classList.remove('moving');
        // 列表元素
        const liElements = document.querySelectorAll(listClassName);
        const sourceIds = [];
        for (let i = 0; i < liElements.length; i++) {
          const childrenDiv = liElements[i].children[0];
          const id = childrenDiv.getAttribute('data-id');
          if (id) {
            sourceIds.push(Number(id));
          }
        }
        this.mixinTargetBuildpackIds = sourceIds;
      };
    },
  },
};
