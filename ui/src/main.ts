import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart, GaugeChart } from 'echarts/charts'
import {
  GridComponent, TooltipComponent, LegendComponent, TitleComponent
} from 'echarts/components'

import App from './App.vue'
import router from './router'

use([CanvasRenderer, BarChart, LineChart, PieChart, GaugeChart,
     GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.component('VChart', VChart)

app.mount('#app')
