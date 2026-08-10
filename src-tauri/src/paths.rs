use std::env;
use std::path::PathBuf;

pub fn app_data_dir() -> PathBuf {
    if let Ok(custom) = env::var("IFORGE_DATA_DIR") {
        return PathBuf::from(custom);
    }
    #[cfg(target_os = "macos")]
    {
        dirs_fallback()
            .join("Library")
            .join("Application Support")
            .join("InfluencerForge")
    }
    #[cfg(target_os = "windows")]
    {
        env::var("APPDATA")
            .map(PathBuf::from)
            .unwrap_or_else(|_| dirs_fallback().join("AppData").join("Roaming"))
            .join("InfluencerForge")
    }
    #[cfg(all(not(target_os = "macos"), not(target_os = "windows")))]
    {
        dirs_fallback().join(".config").join("InfluencerForge")
    }
}

fn dirs_fallback() -> PathBuf {
    env::var("HOME")
        .or_else(|_| env::var("USERPROFILE"))
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."))
}

pub fn resolve_python() -> Option<PathBuf> {
    // Phase 3: prefer embedded portable Python under resources/python
    if let Ok(exe) = env::current_exe() {
        let bundled = exe
            .parent()
            .map(|p| p.join("resources").join("python").join(python_bin_name()))
            .filter(|p| p.exists());
        if bundled.is_some() {
            return bundled;
        }
        // Dev layout: src-tauri/resources/python
        let mut cursor = exe.clone();
        for _ in 0..6 {
            let candidate = cursor
                .join("resources")
                .join("python")
                .join(python_bin_name());
            if candidate.exists() {
                return Some(candidate);
            }
            if let Some(parent) = cursor.parent() {
                cursor = parent.to_path_buf();
            } else {
                break;
            }
        }
    }
    which::which("python3")
        .or_else(|_| which::which("python"))
        .ok()
}

fn python_bin_name() -> &'static str {
    if cfg!(target_os = "windows") {
        "python.exe"
    } else {
        "python"
    }
}

pub fn forge_python_root(app_handle_resource: Option<PathBuf>) -> PathBuf {
    if let Ok(custom) = env::var("IFORGE_PYTHON_ROOT") {
        return PathBuf::from(custom);
    }
    if let Some(res) = app_handle_resource {
        let candidate = res.join("bootstrap");
        if candidate.exists() {
            return candidate;
        }
    }
    // Dev: repository forge-python/
    let cwd = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    if cwd.join("forge-python").exists() {
        return cwd.join("forge-python");
    }
    if cwd
        .parent()
        .map(|p| p.join("forge-python").exists())
        .unwrap_or(false)
    {
        return cwd.parent().unwrap().join("forge-python");
    }
    cwd.join("forge-python")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn data_dir_contains_app_name() {
        let dir = app_data_dir();
        assert!(dir.to_string_lossy().contains("InfluencerForge"));
    }
}
