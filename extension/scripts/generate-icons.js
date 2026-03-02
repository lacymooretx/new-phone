// Run with: node scripts/generate-icons.js
// Generates placeholder extension icons
import { writeFileSync, mkdirSync } from "fs"
import { join, dirname } from "path"
import { fileURLToPath } from "url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const iconsDir = join(__dirname, "..", "icons")

// 1x1 green pixel PNG as minimal placeholder
// Real icons should be designed and replaced before publishing
const sizes = [16, 48, 128]
const PLACEHOLDER_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "base64"
)

try { mkdirSync(iconsDir, { recursive: true }) } catch {}

for (const size of sizes) {
  writeFileSync(join(iconsDir, `icon${size}.png`), PLACEHOLDER_PNG)
  console.log(`Created icon${size}.png (placeholder)`)
}
