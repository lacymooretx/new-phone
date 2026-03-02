import {
  PHONE_REGEX,
  normalizeToE164,
  isLikelyPhoneNumber,
  formatPhoneNumber,
} from "@/shared/phone-regex"
import type { ExtMessage, MessageResponse, ExtensionSettings } from "@/shared/types"

const NP_ATTR = "data-np-click-to-call"
const NP_TOOLTIP_CLASS = "np-c2c-tooltip"

// --- Configuration ---

let numberDetectionEnabled = true
let defaultCountryCode = "1"
let blockedSites: string[] = []

// --- Debounce utility ---

function debounce<T extends (...args: unknown[]) => void>(
  fn: T,
  delay: number,
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | null = null
  return (...args: Parameters<T>) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }
}

// --- Elements to skip ---

const SKIP_TAGS = new Set([
  "SCRIPT",
  "STYLE",
  "TEXTAREA",
  "INPUT",
  "SELECT",
  "CODE",
  "PRE",
  "NOSCRIPT",
  "IFRAME",
  "OBJECT",
  "EMBED",
  "SVG",
  "CANVAS",
  "VIDEO",
  "AUDIO",
  "MAP",
  "HEAD",
])

function shouldSkipNode(node: Node): boolean {
  const parent = node.parentElement
  if (!parent) return true
  // Skip already-wrapped, skip tags, contenteditable
  if (parent.closest(`[${NP_ATTR}]`)) return true
  if (SKIP_TAGS.has(parent.tagName)) return true
  if (parent.closest("[contenteditable]")) return true
  if (parent.isContentEditable) return true
  // Skip invisible elements
  if (parent.offsetParent === null && parent.tagName !== "BODY") return true
  return false
}

// --- Phone number detection and wrapping ---

function wrapPhoneNumbers(root: Node): void {
  if (!numberDetectionEnabled) return

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (shouldSkipNode(node)) return NodeFilter.FILTER_REJECT
      if (!node.textContent || node.textContent.trim().length < 7) {
        return NodeFilter.FILTER_REJECT
      }
      return NodeFilter.FILTER_ACCEPT
    },
  })

  const textNodes: Text[] = []
  let current: Node | null
  while ((current = walker.nextNode())) {
    textNodes.push(current as Text)
  }

  for (const textNode of textNodes) {
    processTextNode(textNode)
  }
}

function processTextNode(textNode: Text): void {
  const text = textNode.textContent
  if (!text) return

  PHONE_REGEX.lastIndex = 0
  const matches: { match: string; index: number }[] = []
  let m: RegExpExecArray | null

  while ((m = PHONE_REGEX.exec(text)) !== null) {
    if (isLikelyPhoneNumber(m[0])) {
      matches.push({ match: m[0], index: m.index })
    }
  }

  if (matches.length === 0) return

  const fragment = document.createDocumentFragment()
  let lastIndex = 0

  for (const { match, index } of matches) {
    // Text before the match
    if (index > lastIndex) {
      fragment.appendChild(
        document.createTextNode(text.slice(lastIndex, index)),
      )
    }

    // Wrapped phone link
    const e164 = normalizeToE164(match)
    const link = document.createElement("a")
    link.href = `tel:${e164}`
    link.setAttribute(NP_ATTR, e164)
    link.className = "np-c2c-link"
    link.textContent = match
    link.title = `Call ${formatPhoneNumber(e164)} via New Phone`
    link.addEventListener("click", onPhoneLinkClick)
    fragment.appendChild(link)

    lastIndex = index + match.length
  }

  // Remaining text
  if (lastIndex < text.length) {
    fragment.appendChild(document.createTextNode(text.slice(lastIndex)))
  }

  textNode.parentNode?.replaceChild(fragment, textNode)
}

// --- Click handler ---

function onPhoneLinkClick(event: Event): void {
  event.preventDefault()
  event.stopPropagation()

  const target = event.currentTarget as HTMLAnchorElement
  const destination = target.getAttribute(NP_ATTR)
  if (!destination) return

  showTooltip(target, destination)
}

function showTooltip(anchor: HTMLElement, destination: string): void {
  // Remove any existing tooltip
  document
    .querySelectorAll(`.${NP_TOOLTIP_CLASS}`)
    .forEach((el) => el.remove())

  const tooltip = document.createElement("div")
  tooltip.className = NP_TOOLTIP_CLASS
  tooltip.innerHTML = `
    <div class="np-c2c-tooltip-header">
      <span class="np-c2c-tooltip-icon">&#128222;</span>
      <span class="np-c2c-tooltip-number">${formatPhoneNumber(destination)}</span>
    </div>
    <button class="np-c2c-btn np-c2c-btn-call" data-action="call" data-dest="${destination}">
      Call with Desk Phone
    </button>
    <button class="np-c2c-btn np-c2c-btn-web" data-action="web" data-dest="${destination}">
      Open in Web Client
    </button>
    <button class="np-c2c-btn np-c2c-btn-copy" data-action="copy" data-dest="${destination}">
      Copy Number
    </button>
  `

  tooltip.addEventListener("click", onTooltipAction)

  // Position near the anchor
  const rect = anchor.getBoundingClientRect()
  tooltip.style.position = "fixed"
  tooltip.style.top = `${rect.bottom + 4}px`
  tooltip.style.left = `${rect.left}px`
  tooltip.style.zIndex = "2147483647"

  // Ensure tooltip stays within viewport
  document.body.appendChild(tooltip)
  const tooltipRect = tooltip.getBoundingClientRect()
  if (tooltipRect.right > window.innerWidth) {
    tooltip.style.left = `${window.innerWidth - tooltipRect.width - 8}px`
  }
  if (tooltipRect.bottom > window.innerHeight) {
    tooltip.style.top = `${rect.top - tooltipRect.height - 4}px`
  }

  // Dismiss on outside click
  const dismiss = (e: MouseEvent) => {
    if (
      !tooltip.contains(e.target as Node) &&
      e.target !== anchor
    ) {
      tooltip.remove()
      document.removeEventListener("click", dismiss)
    }
  }
  setTimeout(() => document.addEventListener("click", dismiss), 0)

  // Dismiss on Escape
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Escape") {
      tooltip.remove()
      document.removeEventListener("keydown", onKey)
      document.removeEventListener("click", dismiss)
    }
  }
  document.addEventListener("keydown", onKey)
}

async function onTooltipAction(event: Event): Promise<void> {
  const btn = (event.target as HTMLElement).closest("button")
  if (!btn) return

  const action = btn.dataset.action
  const dest = btn.dataset.dest
  if (!dest) return

  // Remove tooltip
  btn.closest(`.${NP_TOOLTIP_CLASS}`)?.remove()

  switch (action) {
    case "call":
      sendMessage({
        type: "INITIATE_CALL",
        payload: { destination: dest, method: "originate" },
      })
      break
    case "web":
      sendMessage({
        type: "INITIATE_CALL",
        payload: { destination: dest, method: "web_client" },
      })
      break
    case "copy":
      await navigator.clipboard.writeText(dest)
      showCopiedFeedback()
      break
  }
}

function showCopiedFeedback(): void {
  const toast = document.createElement("div")
  toast.textContent = "Number copied"
  toast.style.cssText = `
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: #1e293b;
    color: #f8fafc;
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 13px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    z-index: 2147483647;
    opacity: 0;
    transition: opacity 0.2s ease;
  `
  document.body.appendChild(toast)
  requestAnimationFrame(() => {
    toast.style.opacity = "1"
  })
  setTimeout(() => {
    toast.style.opacity = "0"
    setTimeout(() => toast.remove(), 200)
  }, 1500)
}

function sendMessage(msg: ExtMessage): Promise<MessageResponse> {
  return chrome.runtime.sendMessage(msg)
}

// --- MutationObserver for dynamic content (debounced) ---

const pendingNodes: Node[] = []

const processPendingNodes = debounce(() => {
  const nodes = pendingNodes.splice(0, pendingNodes.length)
  for (const node of nodes) {
    if (node.isConnected) {
      wrapPhoneNumbers(node)
    }
  }
}, 150)

const observer = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    for (const node of mutation.addedNodes) {
      if (
        node.nodeType === Node.ELEMENT_NODE ||
        node.nodeType === Node.TEXT_NODE
      ) {
        pendingNodes.push(node)
      }
    }
  }
  processPendingNodes()
})

// --- Load settings and check blocked sites ---

function isBlockedSite(hostname: string): boolean {
  return blockedSites.some(
    (pattern) =>
      hostname === pattern || hostname.endsWith(`.${pattern}`),
  )
}

async function loadSettings(): Promise<ExtensionSettings | null> {
  try {
    const resp: MessageResponse = await sendMessage({
      type: "GET_SETTINGS",
    })
    if (resp.success && resp.data) {
      return resp.data as ExtensionSettings
    }
  } catch {
    // Extension context may be invalid
  }
  return null
}

// --- Init ---

async function init(): Promise<void> {
  const settings = await loadSettings()
  if (settings) {
    numberDetectionEnabled = settings.numberDetectionEnabled ?? true
    defaultCountryCode = settings.defaultCountryCode || "1"
    blockedSites = settings.blockedSites || []
  }

  // Check if current site is blocked
  if (isBlockedSite(window.location.hostname)) return

  // Check if detection is enabled
  if (!numberDetectionEnabled) return

  // Scan existing content
  wrapPhoneNumbers(document.body)

  // Watch for dynamic additions
  observer.observe(document.body, {
    childList: true,
    subtree: true,
  })
}

init()
