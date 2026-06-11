import { createRouter, createWebHashHistory } from 'vue-router'
import { useSession } from './stores/session'

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/login', component: () => import('./views/LoginView.vue') },
    { path: '/', component: () => import('./views/ProjectsView.vue') },
    { path: '/help', component: () => import('./views/HelpView.vue') },
    { path: '/users', component: () => import('./views/UsersView.vue') },
    {
      path: '/project/:id',
      component: () => import('./views/ProjectShell.vue'),
      props: true,
      children: [
        { path: '', component: () => import('./views/DashboardView.vue') },
        { path: 'table/:table', component: () => import('./views/TableEditorView.vue'), props: true },
        { path: 'validation', component: () => import('./views/ValidationView.vue') },
        { path: 'io', component: () => import('./views/ImportExportView.vue') },
        { path: 'settings', component: () => import('./views/ProjectSettingsView.vue') },
        { path: 'wizard/packet', component: () => import('./views/PacketWizardView.vue') },
        { path: 'wizard/command', component: () => import('./views/CommandWizardView.vue') },
        { path: 'wizard/calibration', component: () => import('./views/CalibrationWizardView.vue') },
        { path: 'wizard/limit', component: () => import('./views/LimitWizardView.vue') },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const session = useSession()
  if (!session.loaded) await session.load()
  if (to.path !== '/login' && !session.user) return '/login'
  if (to.path === '/login' && session.user) return '/'
})
