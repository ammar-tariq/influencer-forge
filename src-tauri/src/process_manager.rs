use crate::paths::{app_data_dir, forge_python_root, resolve_python};
use anyhow::{anyhow, Context, Result};
use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

pub struct ProcessManager {
    child: Mutex<Option<Child>>,
}

impl Default for ProcessManager {
    fn default() -> Self {
        Self {
            child: Mutex::new(None),
        }
    }
}

impl ProcessManager {
    pub fn start_orchestrator(&self) -> Result<()> {
        // Avoid attaching to a stale server that only knows /api/health.
        self.stop();
        Self::free_port_8765();

        let python = resolve_python().ok_or_else(|| anyhow!("Python 3.10+ not found on PATH"))?;
        let root = forge_python_root(None);
        let data_dir = app_data_dir();
        std::fs::create_dir_all(&data_dir)?;

        // Release: bundled portable Python wins. Dev: prefer uv venv when present.
        let python_exec = {
            let parts: Vec<_> = python.iter().collect();
            let bundled = parts.windows(2).any(|w| {
                w[0] == std::ffi::OsStr::new("resources") && w[1] == std::ffi::OsStr::new("python")
            });
            let venv_python = root.join(".venv").join(if cfg!(target_os = "windows") {
                "Scripts/python.exe"
            } else {
                "bin/python"
            });
            if bundled {
                python
            } else if venv_python.exists() {
                venv_python
            } else {
                python
            }
        };

        let mut cmd = Command::new(&python_exec);
        cmd.current_dir(&root)
            .env("IFORGE_DATA_DIR", &data_dir)
            .env("PYTHONPATH", root.join("src"))
            .arg("-m")
            .arg("forge_python.orchestrator")
            .stdout(Stdio::null())
            .stderr(Stdio::inherit());

        // Pass through optional generation flags from the parent environment.
        for key in [
            "IFORGE_ENABLE_COMFYUI",
            "IFORGE_ALLOW_STUB_FALLBACK",
            "IFORGE_EXTRA_MODEL_DIRS",
            "IFORGE_COMFYUI_ROOT",
            "IFORGE_COMFYUI_PYTHON",
        ] {
            if let Ok(val) = std::env::var(key) {
                cmd.env(key, val);
            }
        }

        let child = cmd
            .spawn()
            .with_context(|| format!("failed to spawn {:?}", python_exec))?;
        *self.child.lock().expect("process mutex") = Some(child);
        Ok(())
    }

    fn free_port_8765() {
        // Best-effort: if something is already listening, try to kill our prior python module.
        if TcpStream::connect_timeout(
            &"127.0.0.1:8765".parse().unwrap(),
            Duration::from_millis(100),
        )
        .is_err()
        {
            return;
        }
        #[cfg(unix)]
        {
            let _ = Command::new("pkill")
                .args(["-f", "forge_python.orchestrator"])
                .status();
            std::thread::sleep(Duration::from_millis(300));
        }
    }

    pub fn stop(&self) {
        if let Ok(mut guard) = self.child.lock() {
            if let Some(child) = guard.as_mut() {
                let _ = child.kill();
                let _ = child.wait();
            }
            *guard = None;
        }
    }

    pub async fn wait_until_healthy(&self, attempts: u32) -> Result<()> {
        let client = reqwest::Client::new();
        for _ in 0..attempts {
            // Prefer readiness — stale servers often only expose /api/health.
            if let Ok(resp) = client.get("http://127.0.0.1:8765/api/readiness").send().await {
                if resp.status().is_success() {
                    return Ok(());
                }
            }
            if let Ok(resp) = client.get("http://127.0.0.1:8765/api/health").send().await {
                if resp.status().is_success() {
                    if let Ok(body) = resp.json::<serde_json::Value>().await {
                        let features = body
                            .get("features")
                            .and_then(|v| v.as_array())
                            .map(|arr| {
                                arr.iter()
                                    .filter_map(|x| x.as_str())
                                    .any(|f| f == "reset")
                            })
                            .unwrap_or(false);
                        if features {
                            return Ok(());
                        }
                    }
                }
            }
            tokio::time::sleep(Duration::from_millis(300)).await;
        }
        Err(anyhow!(
            "orchestrator health check timed out (need /api/readiness or health.features including reset)"
        ))
    }

    pub fn python_root_display(&self) -> PathBuf {
        forge_python_root(None)
    }
}
