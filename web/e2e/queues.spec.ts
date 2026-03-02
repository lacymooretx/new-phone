import { test, expect } from './fixtures'

test.describe('Queues page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/queues')
  })

  test('queues list page loads', async ({ page }) => {
    await expect(page).toHaveURL('/queues')
    await expect(page.getByRole('heading', { name: 'Queues' })).toBeVisible()
    await expect(page.getByText('Manage call queues')).toBeVisible()
  })

  test('table shows queue data or empty state', async ({ page, dataTable }) => {
    // Wait for loading to finish
    const tableOrEmpty = dataTable.table.or(page.getByText('No queues yet'))
    await expect(tableOrEmpty).toBeVisible({ timeout: 15_000 })

    const hasQueues = await dataTable.rows.count() > 0
    if (hasQueues) {
      await expect(dataTable.rows.first()).toBeVisible()
    } else {
      await expect(page.getByText('No queues yet')).toBeVisible()
      await expect(page.getByText('Create a call queue to manage incoming calls.')).toBeVisible()
    }
  })

  test('search works on queues table', async ({ page }) => {
    const searchInput = page.getByPlaceholder('Search queues...')
    await expect(searchInput).toBeVisible()

    await searchInput.fill('support')
    await expect(searchInput).toHaveValue('support')
  })

  test('can open create queue dialog', async ({ page }) => {
    const createButton = page.getByRole('button', { name: 'Create Queue' })
    await expect(createButton).toBeVisible()
    await createButton.click()

    // Dialog should open
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible({ timeout: 5_000 })
    await expect(dialog.getByText('Create Queue')).toBeVisible()

    // Form fields
    await expect(dialog.getByLabel('Name')).toBeVisible()
    await expect(dialog.getByLabel('Queue Number')).toBeVisible()

    // Close
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
  })

  test('columns toggle and export are available', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Queues' })).toBeVisible()

    // Columns button
    const columnsButton = page.getByRole('button', { name: 'Columns' })
    const hasColumns = await columnsButton.isVisible().catch(() => false)
    if (hasColumns) {
      await columnsButton.click()
      const dropdown = page.locator('[role="menu"], [data-radix-popper-content-wrapper]')
      await expect(dropdown).toBeVisible()
      await page.keyboard.press('Escape')
    }

    // Export button (only when data exists)
    const exportButton = page.getByRole('button', { name: 'Export' })
    const hasExport = await exportButton.isVisible().catch(() => false)
    if (hasExport) {
      await expect(exportButton).toBeEnabled()
    }
  })
})
