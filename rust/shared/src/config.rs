use std::env;

/// Helper for loading NP_-prefixed environment variables.
pub struct EnvPrefix;

impl EnvPrefix {
    /// Load a `NP_`-prefixed environment variable.
    /// Returns `Ok(value)` if set, or `Err` with a descriptive message.
    pub fn get(key: &str) -> Result<String, String> {
        let full_key = format!("NP_{}", key);
        env::var(&full_key).map_err(|_| format!("environment variable {} is not set", full_key))
    }

    /// Load a `NP_`-prefixed environment variable with a default.
    pub fn get_or(key: &str, default: &str) -> String {
        let full_key = format!("NP_{}", key);
        env::var(&full_key).unwrap_or_else(|_| default.to_string())
    }

    /// Load a `NP_`-prefixed environment variable and parse it.
    pub fn get_parsed<T: std::str::FromStr>(key: &str, default: T) -> T
    where
        T::Err: std::fmt::Display,
    {
        let full_key = format!("NP_{}", key);
        match env::var(&full_key) {
            Ok(val) => val.parse::<T>().unwrap_or_else(|e| {
                tracing::warn!(
                    key = %full_key,
                    error = %e,
                    "failed to parse env var, using default"
                );
                default
            }),
            Err(_) => default,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_or_default() {
        let val = EnvPrefix::get_or("NONEXISTENT_TEST_KEY_12345", "fallback");
        assert_eq!(val, "fallback");
    }
}
