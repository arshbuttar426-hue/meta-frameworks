pub fn extract_json(raw: &str) -> String {
    let s = raw.trim();
    if s.starts_with("```json") {
        s.strip_prefix("```json").unwrap_or(s).strip_suffix("```").unwrap_or(s).trim().to_string()
    } else if s.starts_with("```") {
        s.strip_prefix("```").unwrap_or(s).strip_suffix("```").unwrap_or(s).trim().to_string()
    } else {
        let start = s.find('{').unwrap_or(0);
        let end = s.rfind('}').map(|i| i + 1).unwrap_or(s.len());
        s[start..end].to_string()
    }
}
