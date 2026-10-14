import { createApp } from 'vue';
import bkui from 'bkui-vue';
import 'bkui-vue/dist/style.css';
import App from './App.vue';
import router from './router';
import './styles/index.css';

const app = createApp(App);

app.use(bkui);
app.use(router);
app.mount('#app');
