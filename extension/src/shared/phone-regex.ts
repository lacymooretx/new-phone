/**
 * Phone number detection regex.
 * Matches common US/Canada and international phone number formats:
 *   - (555) 123-4567, (555) 123 4567
 *   - 555-123-4567, 555.123.4567, 555 123 4567
 *   - +1 (555) 123-4567, +1-555-123-4567, +1.555.123.4567
 *   - +44 20 7123 4567 (international with 1-3 digit country code)
 *   - 1-800-FLOWERS style (ignored - filtered by isLikelyPhoneNumber)
 *   - 10-digit bare: 5551234567
 *   - 11-digit with leading 1: 15551234567
 *   - Toll-free: 1-800-123-4567, 800-123-4567
 *   - Short international: +44 1234 567890
 *   - Extensions: x1234, ext. 1234 (captured separately)
 */

// Combined pattern for efficient scanning
// Group 1: international prefix with +
// Group 2: NANP style numbers
export const PHONE_REGEX =
  /(?:\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?:\s*(?:x|ext\.?)\s*\d{1,6})?|\+\d{1,3}[\s.-]?\d{1,5}[\s.-]?\d{2,5}[\s.-]?\d{2,5}(?:[\s.-]?\d{1,5})?/g

export function normalizeToE164(raw: string): string {
  // Strip extension portion
  const withoutExt = raw.replace(/\s*(?:x|ext\.?)\s*\d+$/i, "")
  const digits = withoutExt.replace(/\D/g, "")

  if (digits.length === 10) return `+1${digits}`
  if (digits.length === 11 && digits.startsWith("1")) return `+${digits}`
  if (digits.length > 10) return `+${digits}`
  return digits
}

export function formatPhoneNumber(e164: string): string {
  const digits = e164.replace(/\D/g, "")
  if (digits.length === 11 && digits.startsWith("1")) {
    return `(${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`
  }
  if (digits.length === 10) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`
  }
  // International: +CC rest
  if (e164.startsWith("+")) return e164
  return `+${digits}`
}

// Short numbers that are NOT phone numbers (years, zip codes, CSS values, etc.)
const FALSE_POSITIVE_PATTERN = /^(19|20)\d{2}$|^\d{5}(-\d{4})?$/

// Sequences of the same digit repeated (e.g. 0000000000, 1111111111)
const REPEATED_DIGIT = /^(\d)\1+$/

// Common non-phone patterns
const NON_PHONE_PREFIXES = [
  "0000", // padding
  "1234", // test sequences
]

export function isLikelyPhoneNumber(text: string): boolean {
  const digits = text.replace(/\D/g, "")

  // Length check: real phone numbers are 7-15 digits
  if (digits.length < 7 || digits.length > 15) return false

  // Filter out years, zip codes
  if (FALSE_POSITIVE_PATTERN.test(digits)) return false

  // Filter out repeated digits (0000000000, etc.)
  if (REPEATED_DIGIT.test(digits)) return false

  // Filter out obvious test/padding sequences
  for (const prefix of NON_PHONE_PREFIXES) {
    if (digits === prefix.repeat(Math.ceil(digits.length / prefix.length)).slice(0, digits.length)) {
      return false
    }
  }

  // If it contains letters, it's probably not a phone number we can dial
  // (except for +, -, (, ), ., space which are already stripped by \D)
  if (/[a-zA-Z]/.test(text.replace(/\s*(?:x|ext\.?)\s*\d+$/i, ""))) return false

  return true
}
