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

fn python_candidates_under(root: &std::path::Path) -> Vec<PathBuf> {
    let bin = python_bin_name();
    vec![
        root.join(bin),
        root.join("bin").join(bin),
        root.join("bin").join("python3"),
        root.join("Scripts").join("python.exe"),
    ]
}

pub fn resolve_python() -> Option<PathBuf> {
    // Prefer embedded portable Python under resources/python (release + assembled dev).
    if let Ok(exe) = env::current_exe() {
        let near_exe = exe
            .parent()
            .map(|p| p.join("resources").join("python"))
            .filter(|p| p.exists());
        if let Some(dir) = near_exe {
            for candidate in python_candidates_under(&dir) {
                if candidate.exists() {
                    return Some(candidate);
                }
            }
        }
        // Dev / CI layout: walk up toward src-tauri/resources/python
        let mut cursor = exe.clone();
        for _ in 0..8 {
            let dir = cursor.join("resources").join("python");
            if dir.exists() {
                for candidate in python_candidates_under(&dir) {
                    if candidate.exists() {
                        return Some(candidate);
                    }
                }
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

fn looks_like_forge_root(path: &std::path::Path) -> bool {
    path.join("src").join("forge_python").exists()
}

pub fn forge_python_root(app_handle_resource: Option<PathBuf>) -> PathBuf {
    if let Ok(custom) = env::var("IFORGE_PYTHON_ROOT") {
        return PathBuf::from(custom);
    }
    if let Some(res) = app_handle_resource {
        let bundled = res.join("forge-python");
        if looks_like_forge_root(&bundled) {
            return bundled;
        }
        let candidate = res.join("bootstrap");
        if candidate.exists() {
            return candidate;
        }
    }
    // Release / assembled: resources/forge-python next to the binary
    if let Ok(exe) = env::current_exe() {
        let mut cursor = exe;
        for _ in 0..8 {
            let bundled = cursor.join("resources").join("forge-python");
            if looks_like_forge_root(&bundled) {
                return bundled;
            }
            if let Some(parent) = cursor.parent() {
                cursor = parent.to_path_buf();
            } else {
                break;
            }
        }
    }
    // Dev: repository forge-python/
    let cwd = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    if looks_like_forge_root(&cwd.join("forge-python")) {
        return cwd.join("forge-python");
    }
    if cwd
        .parent()
        .map(|p| looks_like_forge_root(&p.join("forge-python")))
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
