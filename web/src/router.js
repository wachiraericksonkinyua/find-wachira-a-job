import { createRouter, createWebHistory } from 'vue-router'

import HomePage from './pages/HomePage.vue'
import MatchPage from './pages/MatchPage.vue'
import ProjectsPage from './pages/ProjectsPage.vue'
import WallPage from './pages/WallPage.vue'
import LabPage from './pages/LabPage.vue'
import BoardPage from './pages/BoardPage.vue'
import ApplyPage from './pages/ApplyPage.vue'
import MeetDev from './pages/MeetDev.vue'
import SystemLogs from './pages/SystemLogs.vue'
import AdminDashboard from './pages/AdminDashboard.vue'
import ContactPage from './pages/ContactPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/match', name: 'match', component: MatchPage },
    { path: '/projects', name: 'projects', component: ProjectsPage },
    { path: '/wall', name: 'wall', component: WallPage },
    { path: '/lab', name: 'lab', component: LabPage },
    { path: '/board', name: 'board', component: BoardPage },
    { path: '/apply', name: 'apply', component: ApplyPage },
    { path: '/meet', name: 'meet', component: MeetDev },
    { path: '/logs', name: 'logs', component: SystemLogs },
    { path: '/admin', name: 'admin', component: AdminDashboard },
    {
      path: '/admin/logs',
      name: 'admin-logs',
      component: AdminDashboard,
      props: { initialTab: 'logs' },
    },
    { path: '/contact', name: 'contact', component: ContactPage },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition || { top: 0 }
  },
})

export default router
