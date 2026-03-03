import { useState, useCallback, useRef, useEffect } from "react"
import { useTranslation } from "react-i18next"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { MapPin, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

const API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || ""

export interface AddressFields {
  street: string
  city: string
  state: string
  zip: string
  country: string
}

interface AddressAutocompleteProps {
  value: AddressFields
  onChange: (fields: AddressFields) => void
  labels?: {
    street?: string
    city?: string
    state?: string
    zip?: string
    country?: string
  }
  placeholders?: {
    street?: string
  }
}

interface Suggestion {
  placeId: string
  description: string
}

// Debounce helper
function useDebounce(value: string, delay: number): string {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

async function fetchSuggestions(input: string): Promise<Suggestion[]> {
  if (!API_KEY || input.length < 3) return []
  try {
    const res = await fetch("https://places.googleapis.com/v1/places:autocomplete", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
      },
      body: JSON.stringify({
        input,
        includedPrimaryTypes: ["street_address", "subpremise", "premise", "route"],
        languageCode: "en",
      }),
    })
    if (!res.ok) return []
    const data = await res.json()
    return (data.suggestions || [])
      .filter((s: { placePrediction?: unknown }) => s.placePrediction)
      .map((s: { placePrediction: { placeId: string; text: { text: string } } }) => ({
        placeId: s.placePrediction.placeId,
        description: s.placePrediction.text.text,
      }))
  } catch {
    return []
  }
}

async function fetchPlaceDetails(placeId: string): Promise<AddressFields | null> {
  if (!API_KEY) return null
  try {
    const res = await fetch(
      `https://places.googleapis.com/v1/places/${placeId}?languageCode=en`,
      {
        headers: {
          "X-Goog-Api-Key": API_KEY,
          "X-Goog-FieldMask": "addressComponents",
        },
      }
    )
    if (!res.ok) return null
    const data = await res.json()
    const components: { types: string[]; shortText: string; longText: string }[] =
      data.addressComponents || []

    const get = (type: string, useShort = false): string => {
      const c = components.find((c) => c.types.includes(type))
      return c ? (useShort ? c.shortText : c.longText) : ""
    }

    const streetNumber = get("street_number")
    const route = get("route")
    const street = [streetNumber, route].filter(Boolean).join(" ")

    return {
      street,
      city: get("locality") || get("sublocality") || get("administrative_area_level_3"),
      state: get("administrative_area_level_1", true),
      zip: get("postal_code"),
      country: get("country", true),
    }
  } catch {
    return null
  }
}

export function AddressAutocomplete({
  value,
  onChange,
  labels,
  placeholders,
}: AddressAutocompleteProps) {
  const { t } = useTranslation()
  const [query, setQuery] = useState("")
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [loading, setLoading] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const containerRef = useRef<HTMLDivElement>(null)
  const debouncedQuery = useDebounce(query, 300)
  const apiAvailable = !!API_KEY

  // Fetch suggestions on debounced query change
  useEffect(() => {
    if (!apiAvailable || debouncedQuery.length < 3) {
      setSuggestions([])
      return
    }
    let cancelled = false
    setLoading(true)
    fetchSuggestions(debouncedQuery).then((results) => {
      if (!cancelled) {
        setSuggestions(results)
        setShowDropdown(results.length > 0)
        setSelectedIndex(-1)
        setLoading(false)
      }
    })
    return () => { cancelled = true }
  }, [debouncedQuery, apiAvailable])

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  const selectSuggestion = useCallback(
    async (suggestion: Suggestion) => {
      setShowDropdown(false)
      setLoading(true)
      const details = await fetchPlaceDetails(suggestion.placeId)
      setLoading(false)
      if (details) {
        onChange(details)
        setQuery("")
      }
    },
    [onChange]
  )

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown || suggestions.length === 0) return
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setSelectedIndex((i) => Math.min(i + 1, suggestions.length - 1))
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setSelectedIndex((i) => Math.max(i - 1, 0))
    } else if (e.key === "Enter" && selectedIndex >= 0) {
      e.preventDefault()
      selectSuggestion(suggestions[selectedIndex])
    } else if (e.key === "Escape") {
      setShowDropdown(false)
    }
  }

  const handleFieldChange = useCallback(
    (field: keyof AddressFields, val: string) => {
      onChange({ ...value, [field]: val })
    },
    [value, onChange]
  )

  const streetLabel = labels?.street || t("sites.form.street", "Street Address")
  const cityLabel = labels?.city || t("sites.form.city", "City")
  const stateLabel = labels?.state || t("sites.form.state", "State")
  const zipLabel = labels?.zip || t("sites.form.zip", "ZIP Code")
  const countryLabel = labels?.country || t("sites.form.country", "Country")
  const streetPlaceholder = placeholders?.street || t("sites.form.streetPlaceholder", "123 Main St")

  return (
    <div className="space-y-4">
      {apiAvailable && (
        <div className="space-y-2" ref={containerRef}>
          <Label>{t("sites.form.addressSearch", "Search Address")}</Label>
          <div className="relative">
            <Input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value)
                if (e.target.value.length < 3) setShowDropdown(false)
              }}
              onFocus={() => { if (suggestions.length > 0) setShowDropdown(true) }}
              onKeyDown={handleKeyDown}
              placeholder={t("sites.form.addressSearchPlaceholder", "Start typing an address...")}
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
              {loading ? (
                <Loader2 className="h-4 w-4 text-muted-foreground animate-spin" />
              ) : (
                <MapPin className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          </div>
          <p className="text-xs text-muted-foreground">{t("sites.form.addressSearchHelp", "Type to search — address fields fill automatically")}</p>

          {showDropdown && suggestions.length > 0 && (
            <ul className="absolute z-50 mt-1 w-full max-w-[calc(100%-3rem)] rounded-md border bg-popover shadow-md">
              {suggestions.map((s, i) => (
                <li
                  key={s.placeId}
                  className={cn(
                    "cursor-pointer px-3 py-2 text-sm hover:bg-accent",
                    i === selectedIndex && "bg-accent"
                  )}
                  onMouseDown={() => selectSuggestion(s)}
                  onMouseEnter={() => setSelectedIndex(i)}
                >
                  <MapPin className="mr-2 inline h-3.5 w-3.5 text-muted-foreground" />
                  {s.description}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="space-y-2">
        <Label>{streetLabel}</Label>
        <Input
          value={value.street}
          onChange={(e) => handleFieldChange("street", e.target.value)}
          placeholder={streetPlaceholder}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <div className="space-y-2">
          <Label>{cityLabel}</Label>
          <Input
            value={value.city}
            onChange={(e) => handleFieldChange("city", e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>{stateLabel}</Label>
          <Input
            value={value.state}
            onChange={(e) => handleFieldChange("state", e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>{zipLabel}</Label>
          <Input
            value={value.zip}
            onChange={(e) => handleFieldChange("zip", e.target.value)}
          />
        </div>
      </div>

      <div className="max-w-xs space-y-2">
        <Label>{countryLabel}</Label>
        <Input
          value={value.country}
          onChange={(e) => handleFieldChange("country", e.target.value)}
          placeholder="US"
        />
      </div>
    </div>
  )
}
