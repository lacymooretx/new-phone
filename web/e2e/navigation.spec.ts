import { test, expect } from './fixtures'

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    // Ensure the dashboard loads fully
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  })

  test('sidebar shows all major navigation groups', async ({ page: _page, sidebar }) => {
    await expect(sidebar.root).toBeVisible()

    // Top-level nav -- Dashboard is always visible
    await expect(sidebar.navLink('Dashboard')).toBeVisible()

    // Telephony group
    await expect(sidebar.groupLabel('Telephony')).toBeVisible()
    await expect(sidebar.navLink('Extensions')).toBeVisible()
    await expect(sidebar.navLink('Ring Groups')).toBeVisible()
    await expect(sidebar.navLink('Queues')).toBeVisible()
    await expect(sidebar.navLink('IVR Menus')).toBeVisible()
    await expect(sidebar.navLink('Conferences')).toBeVisible()
    await expect(sidebar.navLink('Paging')).toBeVisible()
    await expect(sidebar.navLink('Devices')).toBeVisible()

    // Connectivity group
    await expect(sidebar.groupLabel('Connectivity')).toBeVisible()
    await expect(sidebar.navLink('SIP Trunks')).toBeVisible()
    await expect(sidebar.navLink('DIDs')).toBeVisible()
    await expect(sidebar.navLink('Inbound Routes')).toBeVisible()
    await expect(sidebar.navLink('Outbound Routes')).toBeVisible()

    // Reports group
    await expect(sidebar.groupLabel('Reports')).toBeVisible()
    await expect(sidebar.navLink('Call History')).toBeVisible()
    await expect(sidebar.navLink('Recordings')).toBeVisible()
    await expect(sidebar.navLink('Voicemail')).toBeVisible()

    // System group
    await expect(sidebar.groupLabel('System')).toBeVisible()
    await expect(sidebar.navLink('Users')).toBeVisible()
    await expect(sidebar.navLink('Settings')).toBeVisible()
    await expect(sidebar.navLink('Audit Logs')).toBeVisible()
  })

  test('clicking nav item navigates to correct page', async ({ page, sidebar }) => {
    // Extensions
    await sidebar.navLink('Extensions').click()
    await expect(page).toHaveURL('/extensions')
    await expect(page.getByRole('heading', { name: 'Extensions' })).toBeVisible()

    // Queues
    await sidebar.navLink('Queues').click()
    await expect(page).toHaveURL('/queues')
    await expect(page.getByRole('heading', { name: 'Queues' })).toBeVisible()

    // Call History
    await sidebar.navLink('Call History').click()
    await expect(page).toHaveURL('/cdrs')

    // Users
    await sidebar.navLink('Users').click()
    await expect(page).toHaveURL('/users')
    await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible()

    // Voicemail
    await sidebar.navLink('Voicemail').click()
    await expect(page).toHaveURL('/voicemail')

    // Recordings
    await sidebar.navLink('Recordings').click()
    await expect(page).toHaveURL('/recordings')

    // Settings
    await sidebar.navLink('Settings').click()
    await expect(page).toHaveURL('/settings')
  })

  test('active nav item is highlighted', async ({ page, sidebar }) => {
    // On dashboard, the Dashboard link should have the active class
    const dashboardLink = sidebar.navLink('Dashboard')
    await expect(dashboardLink).toHaveClass(/bg-sidebar-accent/)

    // Navigate to Extensions
    await sidebar.navLink('Extensions').click()
    await expect(page).toHaveURL('/extensions')

    // Extensions should now be active
    const extensionsLink = sidebar.navLink('Extensions')
    await expect(extensionsLink).toHaveClass(/bg-sidebar-accent/)

    // Dashboard should no longer be active
    await expect(dashboardLink).not.toHaveClass(/bg-sidebar-accent/)
  })

  test('browser back/forward works', async ({ page, sidebar }) => {
    // Start at dashboard
    await expect(page).toHaveURL('/')

    // Navigate to Extensions
    await sidebar.navLink('Extensions').click()
    await expect(page).toHaveURL('/extensions')

    // Navigate to Users
    await sidebar.navLink('Users').click()
    await expect(page).toHaveURL('/users')

    // Go back -- should return to Extensions
    await page.goBack()
    await expect(page).toHaveURL('/extensions')
    await expect(page.getByRole('heading', { name: 'Extensions' })).toBeVisible()

    // Go back again -- should return to Dashboard
    await page.goBack()
    await expect(page).toHaveURL('/')
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()

    // Go forward -- should go to Extensions
    await page.goForward()
    await expect(page).toHaveURL('/extensions')
    await expect(page.getByRole('heading', { name: 'Extensions' })).toBeVisible()

    // Go forward again -- should go to Users
    await page.goForward()
    await expect(page).toHaveURL('/users')
    await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible()
  })

  test('header user menu is functional', async ({ page }) => {
    // The header should have a user avatar button
    const avatarButton = page.locator('header').getByRole('button').filter({ has: page.locator('span') }).last()
    await expect(avatarButton).toBeVisible()
    await avatarButton.click()

    // Dropdown menu should appear
    const menu = page.locator('[role="menu"]')
    await expect(menu).toBeVisible()

    // Should show Profile and Log out options
    await expect(page.getByRole('menuitem', { name: 'Profile' })).toBeVisible()
    await expect(page.getByRole('menuitem', { name: 'Log out' })).toBeVisible()

    // Click Profile to navigate
    await page.getByRole('menuitem', { name: 'Profile' }).click()
    await expect(page).toHaveURL('/profile')
  })

  test('command palette search button is visible in header', async ({ page }) => {
    // The search button is visible on medium+ screens
    const searchButton = page.locator('header button, header [role="button"]').filter({ hasText: 'Search' })
    // On desktop viewport it should be visible
    const isDesktop = (page.viewportSize()?.width ?? 0) >= 768
    if (isDesktop) {
      await expect(searchButton).toBeVisible()
    }
  })

  test('navigating to invalid route shows 404 page', async ({ page }) => {
    await page.goto('/this-route-does-not-exist-12345')

    // Should show the Not Found page
    await expect(page.getByText('Page Not Found')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText("The page you're looking for doesn't exist or has been moved.")).toBeVisible()

    // Should have a link back to dashboard
    const dashboardButton = page.getByRole('link', { name: /dashboard/i }).or(
      page.getByRole('button', { name: /dashboard/i })
    )
    await expect(dashboardButton).toBeVisible()
  })
})
