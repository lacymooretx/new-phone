import { test, expect } from './fixtures'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('dashboard page loads after login', async ({ page, dashboard }) => {
    await expect(page).toHaveURL('/')
    await expect(dashboard.heading).toBeVisible()
    await expect(page.getByText('System overview')).toBeVisible()
  })

  test('shows stat cards or loading skeletons', async ({ page }) => {
    // The dashboard shows 5 stat cards in a grid (Extensions, Users, System Health, Calls Today, Avg Duration).
    // They may be loading (skeletons) or loaded (stat cards with icons).
    // Wait for at least one stat card or skeleton to appear.
    const statCardOrSkeleton = page.locator('[data-slot="skeleton"], h1.text-2xl, .text-2xl.font-bold')
    await expect(statCardOrSkeleton.first()).toBeVisible({ timeout: 10_000 })
  })

  test('sidebar navigation is visible', async ({ sidebar }) => {
    await expect(sidebar.root).toBeVisible()
    await expect(sidebar.brandLink).toBeVisible()
    await expect(sidebar.brandLink).toHaveText('New Phone')

    // Check key nav items are present
    await expect(sidebar.navLink('Dashboard')).toBeVisible()
    await expect(sidebar.navLink('Extensions')).toBeVisible()
    await expect(sidebar.navLink('Users')).toBeVisible()
    await expect(sidebar.navLink('Queues')).toBeVisible()
  })

  test('can navigate to different sections via sidebar', async ({ page, sidebar }) => {
    // Navigate to Extensions
    await sidebar.navLink('Extensions').click()
    await expect(page).toHaveURL('/extensions')
    await expect(page.getByRole('heading', { name: 'Extensions' })).toBeVisible()

    // Navigate to Users
    await sidebar.navLink('Users').click()
    await expect(page).toHaveURL('/users')
    await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible()

    // Navigate back to Dashboard
    await sidebar.navLink('Dashboard').click()
    await expect(page).toHaveURL('/')
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  })

  test('quick actions card is visible with navigation buttons', async ({ page }) => {
    // Wait for dashboard to load
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()

    // Quick Actions section
    await expect(page.getByText('Quick Actions')).toBeVisible()

    // Check specific quick action buttons
    const extensionButton = page.getByRole('button', { name: /Extension/i }).first()
    await expect(extensionButton).toBeVisible()

    const userButton = page.getByRole('button', { name: /User/i }).first()
    await expect(userButton).toBeVisible()
  })

  test('recent calls section is visible', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()

    // Recent Calls heading
    await expect(page.getByText('Recent Calls')).toBeVisible()

    // Either the calls table or the "No recent calls" message should be visible
    const callsTable = page.locator('table').last()
    const noCallsMessage = page.getByText('No recent calls')
    await expect(callsTable.or(noCallsMessage)).toBeVisible({ timeout: 10_000 })
  })
})
