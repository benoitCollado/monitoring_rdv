import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/monitor' },
  {
    path: '/monitor',
    name: 'monitor',
    component: () => import('@/views/MonitorView.vue'),
  },
  {
    path: '/links/:linkId',
    name: 'link-detail',
    component: () => import('@/views/LinkDetailView.vue'),
  },
  {
    path: '/runs',
    name: 'runs',
    component: () => import('@/views/RunsView.vue'),
  },
  {
    path: '/shops',
    name: 'shops',
    component: () => import('@/views/ShopsView.vue'),
  },
  {
    path: '/employees',
    name: 'employees',
    component: () => import('@/views/EmployeesView.vue'),
  },
  {
    path: '/appointment-types',
    name: 'appointment-types',
    component: () => import('@/views/AppointmentTypesView.vue'),
  },
  {
    path: '/companies',
    name: 'companies',
    component: () => import('@/views/CompaniesView.vue'),
  },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
