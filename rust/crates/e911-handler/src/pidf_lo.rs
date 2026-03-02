use serde::{Deserialize, Serialize};

/// Civic address for PIDF-LO (RFC 4119 / RFC 5139).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CivicAddress {
    /// Country code (ISO 3166-1 alpha-2)
    pub country: String,
    /// State/province (A1)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub state: Option<String>,
    /// County/region (A2)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub county: Option<String>,
    /// City (A3)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub city: Option<String>,
    /// Street name (A6)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub street: Option<String>,
    /// House number (HNO)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub house_number: Option<String>,
    /// House number suffix (HNS)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub house_number_suffix: Option<String>,
    /// Floor (FLR)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub floor: Option<String>,
    /// Room (ROOM)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub room: Option<String>,
    /// Postal code (PC)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub postal_code: Option<String>,
    /// Location name/description (LOC)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub location_name: Option<String>,
}

/// Geographic coordinates for PIDF-LO.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeoCoordinates {
    pub latitude: f64,
    pub longitude: f64,
    /// Altitude in meters (optional)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub altitude: Option<f64>,
    /// Uncertainty radius in meters
    #[serde(skip_serializing_if = "Option::is_none")]
    pub uncertainty: Option<f64>,
}

/// Per-extension location record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtensionLocation {
    pub extension: String,
    pub tenant_id: String,
    pub civic_address: CivicAddress,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub geo_coordinates: Option<GeoCoordinates>,
    pub updated_at: u64,
}

/// Build a PIDF-LO XML document per RFC 4119.
pub fn build_pidf_lo(location: &ExtensionLocation) -> String {
    let entity = format!(
        "pres:{}@pbx.local",
        location.extension
    );

    let civic_xml = build_civic_address_xml(&location.civic_address);
    let geo_xml = location
        .geo_coordinates
        .as_ref()
        .map(build_geo_xml)
        .unwrap_or_default();

    format!(
        r#"<?xml version="1.0" encoding="UTF-8"?>
<presence xmlns="urn:ietf:params:xml:ns:pidf"
          xmlns:gp="urn:ietf:params:xml:ns:pidf:geopriv10"
          xmlns:ca="urn:ietf:params:xml:ns:pidf:geopriv10:civicAddr"
          xmlns:gml="http://www.opengis.net/gml"
          entity="{entity}">
  <tuple id="{extension}-location">
    <status>
      <gp:geopriv>
        <gp:location-info>
{civic_xml}{geo_xml}
        </gp:location-info>
        <gp:usage-rules>
          <gp:retransmission-allowed>yes</gp:retransmission-allowed>
        </gp:usage-rules>
      </gp:geopriv>
    </status>
    <timestamp>{timestamp}</timestamp>
  </tuple>
</presence>"#,
        entity = entity,
        extension = location.extension,
        civic_xml = civic_xml,
        geo_xml = geo_xml,
        timestamp = format_rfc3339(location.updated_at),
    )
}

fn build_civic_address_xml(addr: &CivicAddress) -> String {
    let mut parts = Vec::new();
    parts.push("          <ca:civicAddress>".to_string());
    parts.push(format!("            <ca:country>{}</ca:country>", addr.country));

    if let Some(ref v) = addr.state {
        parts.push(format!("            <ca:A1>{}</ca:A1>", v));
    }
    if let Some(ref v) = addr.county {
        parts.push(format!("            <ca:A2>{}</ca:A2>", v));
    }
    if let Some(ref v) = addr.city {
        parts.push(format!("            <ca:A3>{}</ca:A3>", v));
    }
    if let Some(ref v) = addr.street {
        parts.push(format!("            <ca:A6>{}</ca:A6>", v));
    }
    if let Some(ref v) = addr.house_number {
        parts.push(format!("            <ca:HNO>{}</ca:HNO>", v));
    }
    if let Some(ref v) = addr.house_number_suffix {
        parts.push(format!("            <ca:HNS>{}</ca:HNS>", v));
    }
    if let Some(ref v) = addr.floor {
        parts.push(format!("            <ca:FLR>{}</ca:FLR>", v));
    }
    if let Some(ref v) = addr.room {
        parts.push(format!("            <ca:ROOM>{}</ca:ROOM>", v));
    }
    if let Some(ref v) = addr.postal_code {
        parts.push(format!("            <ca:PC>{}</ca:PC>", v));
    }
    if let Some(ref v) = addr.location_name {
        parts.push(format!("            <ca:LOC>{}</ca:LOC>", v));
    }

    parts.push("          </ca:civicAddress>".to_string());
    parts.join("\n")
}

fn build_geo_xml(geo: &GeoCoordinates) -> String {
    let altitude_xml = geo
        .altitude
        .map(|a| format!("\n              <gml:altitude>{}</gml:altitude>", a))
        .unwrap_or_default();

    format!(
        r#"
          <gml:Point srsName="urn:ogc:def:crs:EPSG::4326">
            <gml:pos>{lat} {lon}</gml:pos>{altitude}
          </gml:Point>"#,
        lat = geo.latitude,
        lon = geo.longitude,
        altitude = altitude_xml,
    )
}

fn format_rfc3339(epoch: u64) -> String {
    // Simple RFC 3339 timestamp from epoch seconds
    let secs = epoch;
    let days_since_epoch = secs / 86400;
    let time_of_day = secs % 86400;

    let hours = time_of_day / 3600;
    let minutes = (time_of_day % 3600) / 60;
    let seconds = time_of_day % 60;

    // Calculate date from days since 1970-01-01
    let (year, month, day) = days_to_date(days_since_epoch);

    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z",
        year, month, day, hours, minutes, seconds
    )
}

fn days_to_date(days: u64) -> (u64, u64, u64) {
    // Simplified date calculation
    let mut remaining = days;
    let mut year = 1970u64;

    loop {
        let days_in_year = if is_leap_year(year) { 366 } else { 365 };
        if remaining < days_in_year {
            break;
        }
        remaining -= days_in_year;
        year += 1;
    }

    let month_days = if is_leap_year(year) {
        [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    } else {
        [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    };

    let mut month = 1u64;
    for &days_in_month in &month_days {
        let dim = days_in_month as u64;
        if remaining < dim {
            break;
        }
        remaining -= dim;
        month += 1;
    }

    (year, month, remaining + 1)
}

fn is_leap_year(year: u64) -> bool {
    (year.is_multiple_of(4) && !year.is_multiple_of(100)) || year.is_multiple_of(400)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_build_pidf_lo() {
        let location = ExtensionLocation {
            extension: "1001".to_string(),
            tenant_id: "tenant1".to_string(),
            civic_address: CivicAddress {
                country: "US".to_string(),
                state: Some("CA".to_string()),
                county: None,
                city: Some("San Francisco".to_string()),
                street: Some("Market Street".to_string()),
                house_number: Some("100".to_string()),
                house_number_suffix: None,
                floor: Some("3".to_string()),
                room: Some("301".to_string()),
                postal_code: Some("94105".to_string()),
                location_name: Some("Main Office".to_string()),
            },
            geo_coordinates: Some(GeoCoordinates {
                latitude: 37.7749,
                longitude: -122.4194,
                altitude: None,
                uncertainty: None,
            }),
            updated_at: 1700000000,
        };

        let xml = build_pidf_lo(&location);
        assert!(xml.contains("urn:ietf:params:xml:ns:pidf"));
        assert!(xml.contains("Market Street"));
        assert!(xml.contains("San Francisco"));
        assert!(xml.contains("37.7749"));
    }

    #[test]
    fn test_build_pidf_lo_civic_address_only() {
        let location = ExtensionLocation {
            extension: "2001".to_string(),
            tenant_id: "tenant2".to_string(),
            civic_address: CivicAddress {
                country: "US".to_string(),
                state: Some("TX".to_string()),
                county: Some("Travis".to_string()),
                city: Some("Austin".to_string()),
                street: Some("Congress Avenue".to_string()),
                house_number: Some("500".to_string()),
                house_number_suffix: Some("B".to_string()),
                floor: None,
                room: None,
                postal_code: Some("78701".to_string()),
                location_name: None,
            },
            geo_coordinates: None,
            updated_at: 1700000000,
        };

        let xml = build_pidf_lo(&location);

        // Verify required XML structure
        assert!(xml.contains("<?xml version=\"1.0\""));
        assert!(xml.contains("urn:ietf:params:xml:ns:pidf"));
        assert!(xml.contains("urn:ietf:params:xml:ns:pidf:geopriv10:civicAddr"));
        assert!(xml.contains("pres:2001@pbx.local"));

        // Verify civic address fields
        assert!(xml.contains("<ca:country>US</ca:country>"));
        assert!(xml.contains("<ca:A1>TX</ca:A1>"));
        assert!(xml.contains("<ca:A2>Travis</ca:A2>"));
        assert!(xml.contains("<ca:A3>Austin</ca:A3>"));
        assert!(xml.contains("<ca:A6>Congress Avenue</ca:A6>"));
        assert!(xml.contains("<ca:HNO>500</ca:HNO>"));
        assert!(xml.contains("<ca:HNS>B</ca:HNS>"));
        assert!(xml.contains("<ca:PC>78701</ca:PC>"));

        // Should NOT contain geo coordinates (Point/pos)
        assert!(!xml.contains("<gml:Point"));
        assert!(!xml.contains("<gml:pos>"));

        // Should NOT contain optional fields that were None
        assert!(!xml.contains("<ca:FLR>"));
        assert!(!xml.contains("<ca:ROOM>"));
        assert!(!xml.contains("<ca:LOC>"));
    }

    #[test]
    fn test_build_pidf_lo_with_coordinates() {
        let location = ExtensionLocation {
            extension: "3001".to_string(),
            tenant_id: "tenant3".to_string(),
            civic_address: CivicAddress {
                country: "US".to_string(),
                state: Some("NY".to_string()),
                county: None,
                city: Some("New York".to_string()),
                street: Some("Broadway".to_string()),
                house_number: Some("1".to_string()),
                house_number_suffix: None,
                floor: Some("42".to_string()),
                room: Some("4200".to_string()),
                postal_code: Some("10004".to_string()),
                location_name: Some("Tower Office".to_string()),
            },
            geo_coordinates: Some(GeoCoordinates {
                latitude: 40.7128,
                longitude: -74.0060,
                altitude: Some(150.5),
                uncertainty: None,
            }),
            updated_at: 1700000000,
        };

        let xml = build_pidf_lo(&location);

        // Verify geo coordinates
        assert!(xml.contains("<gml:Point srsName=\"urn:ogc:def:crs:EPSG::4326\">"));
        assert!(xml.contains("40.7128 -74.006"));
        assert!(xml.contains("<gml:altitude>150.5</gml:altitude>"));

        // Verify civic address is also present
        assert!(xml.contains("<ca:A3>New York</ca:A3>"));
        assert!(xml.contains("<ca:FLR>42</ca:FLR>"));
        assert!(xml.contains("<ca:ROOM>4200</ca:ROOM>"));
        assert!(xml.contains("<ca:LOC>Tower Office</ca:LOC>"));

        // Verify entity and tuple id
        assert!(xml.contains("entity=\"pres:3001@pbx.local\""));
        assert!(xml.contains("id=\"3001-location\""));
    }

    #[test]
    fn test_format_rfc3339() {
        // 2023-11-14T22:13:20Z = epoch 1700000000
        let result = format_rfc3339(1700000000);
        assert_eq!(result, "2023-11-14T22:13:20Z");
    }

    #[test]
    fn test_format_rfc3339_epoch_zero() {
        let result = format_rfc3339(0);
        assert_eq!(result, "1970-01-01T00:00:00Z");
    }
}
