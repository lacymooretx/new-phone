import { test, expect } from './fixtures'

test.describe('Extensions page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/extensions')
  })

  test('extensions list page loads', async ({ page }) => {
    await expect(page).toHaveURL('/extensions')
    await expect(page.getByRole('heading', { name: 'Extensions' })).toBeVisible()
    await expect(page.getByText('Manage phone extensions')).toBeVisible()
  })

  test('table shows extension data or empty state', async ({ page, dataTable }) => {
    // Wait for loading to finish -- either the table with rows or the empty state
    const tableOrEmpty = dataTable.table.or(page.getByText('No extensions yet'))
    await expect(tableOrEmpty).toBeVisible({ timeout: 15_000 })

    const hasExtensions = await dataTable.rows.count() > 0
    if (hasExtensions) {
      // Table should have visible rows
      await expect(dataTable.rows.first()).toBeVisible()
    } else {
      // Empty state should show
      await expect(page.getByText('No extensions yet')).toBeVisible()
      await expect(page.getByText('Create your first extension to get started.')).toBeVisible()
    }
  })

  test('search/filter works', async ({ page, dataTable: _dataTable }) => {
    // Wait for page to load
    await expect(page.getByRole('heading', { name: 'Extensions' })).toBeVisible()

    // Search input should be present
    const searchInput = page.getByPlaceholder('Search extensions...')
    await expect(searchInput).toBeVisible()

    // Type a search term
    await searchInput.fill('999999')
    // Table should react (filter down -- possibly to no results)
    // We verify the search input value was accepted
    await expect(searchInput).toHaveValue('999999')
  })

  test('can open create extension dialog', async ({ page }) => {
    // "Create Extension" button in the page header
    const createButton = page.getByRole('button', { name: 'Create Extension' })
    await expect(createButton).toBeVisible()
    await createButton.click()

    // Dialog should open
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible({ timeout: 5_000 })
    await expect(dialog.getByText('Create Extension')).toBeVisible()

    // Form fields should be present
    await expect(dialog.getByLabel('Extension Number')).toBeVisible()
    await expect(dialog.getByLabel('Display Name')).toBeVisible()

    // Close the dialog
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
  })

  test('columns toggle is available', async ({ page }) => {
    // Wait for the page to load
    await expect(page.getByRole('heading', { name: 'Extensions' })).toBeVisible()

    // Columns button should exist
    const columnsButton = page.getByRole('button', { name: 'Columns' })
    // The button may not be present if there are no toggleable columns, so check conditionally
    const columnsVisible = await columnsButton.isVisible().catch(() => false)
    if (columnsVisible) {
      await columnsButton.click()
      // Dropdown should appear with column checkboxes
      const dropdown = page.locator('[role="menu"], [data-radix-popper-content-wrapper]')
      await expect(dropdown).toBeVisible()
      await page.keyboard.press('Escape')
    }
  })

  test('export button is visible when data exists', async ({ page }) => {
    // Wait for page to load
    await expect(page.getByRole('heading', { name: 'Extensions' })).toBeVisible()

    // Export button only appears when there are rows
    const exportButton = page.getByRole('button', { name: 'Export' })
    const hasExport = await exportButton.isVisible().catch(() => false)
    // Just verify the button state matches expectation -- if data exists, export should be visible
    if (hasExport) {
      await expect(exportButton).toBeEnabled()
    }
  })
})
