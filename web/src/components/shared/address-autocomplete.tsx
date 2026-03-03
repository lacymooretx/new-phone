import { useEffect, useRef, useState, useCallback } from "react"
import { useTranslation } from "react-i18next"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { MapPin } from "lucide-react"

const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || ""

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

// Track script loading globally
let googleMapsLoaded = false
let googleMapsLoading = false
let googleMapsCallbacks: (() => void)[] = []

function loadGoogleMapsScript(): Promise<void> {
  if (googleMapsLoaded) return Promise.resolve()
  if (!GOOGLE_MAPS_API_KEY) return Promise.reject(new Error("No API key"))

  return new Promise((resolve, reject) => {
    if (googleMapsLoading) {
      googleMapsCallbacks.push(resolve)
      return
    }
    googleMapsLoading = true

    const script = document.createElement("script")
    script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=places`
    script.async = true
    script.onload = () => {
      googleMapsLoaded = true
      googleMapsLoading = false
      resolve()
      googleMapsCallbacks.forEach((cb) => cb())
      googleMapsCallbacks = []
    }
    script.onerror = () => {
      googleMapsLoading = false
      reject(new Error("Failed to load Google Maps"))
      googleMapsCallbacks = []
    }
    document.head.appendChild(script)
  })
}

function parsePlace(place: google.maps.places.PlaceResult): AddressFields {
  const components = place.address_components || []
  const get = (type: string, useShort = false): string => {
    const c = components.find((c) => c.types.includes(type))
    return c ? (useShort ? c.short_name : c.long_name) : ""
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
}

export function AddressAutocomplete({
  value,
  onChange,
  labels,
  placeholders,
}: AddressAutocompleteProps) {
  const { t } = useTranslation()
  const inputRef = useRef<HTMLInputElement>(null)
  const autocompleteRef = useRef<google.maps.places.Autocomplete | null>(null)
  const [apiAvailable, setApiAvailable] = useState(false)

  const handleFieldChange = useCallback(
    (field: keyof AddressFields, val: string) => {
      onChange({ ...value, [field]: val })
    },
    [value, onChange]
  )

  useEffect(() => {
    if (!GOOGLE_MAPS_API_KEY) return

    loadGoogleMapsScript()
      .then(() => {
        setApiAvailable(true)
        if (inputRef.current && !autocompleteRef.current) {
          const autocomplete = new google.maps.places.Autocomplete(inputRef.current, {
            types: ["address"],
            fields: ["address_components", "formatted_address"],
          })
          autocomplete.addListener("place_changed", () => {
            const place = autocomplete.getPlace()
            if (place.address_components) {
              onChange(parsePlace(place))
            }
          })
          autocompleteRef.current = autocomplete
        }
      })
      .catch(() => {
        // API unavailable, fall back to manual entry
      })
  }, [onChange])

  const streetLabel = labels?.street || t("sites.form.street", "Street Address")
  const cityLabel = labels?.city || t("sites.form.city", "City")
  const stateLabel = labels?.state || t("sites.form.state", "State")
  const zipLabel = labels?.zip || t("sites.form.zip", "ZIP Code")
  const countryLabel = labels?.country || t("sites.form.country", "Country")
  const streetPlaceholder = placeholders?.street || t("sites.form.streetPlaceholder", "123 Main St")

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>{streetLabel}</Label>
        <div className="relative">
          <Input
            ref={inputRef}
            value={value.street}
            onChange={(e) => handleFieldChange("street", e.target.value)}
            placeholder={apiAvailable ? t("sites.form.addressSearchPlaceholder", "Start typing an address...") : streetPlaceholder}
          />
          {apiAvailable && (
            <MapPin className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          )}
        </div>
        {apiAvailable && (
          <p className="text-xs text-muted-foreground">{t("sites.form.addressSearchHelp", "Type to search — address fields fill automatically")}</p>
        )}
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
