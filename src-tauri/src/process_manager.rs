use crate::paths::{app_data_dir, forge_python_root, resolve_python};
use anyhow::{anyhow, Context, Result};
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
        let python = resolve_python().ok_or_else(|| anyhow!("Python 3.10+ not found on PATH"))?;
        let root = forge_python_root(None);
        let data_dir = app_data_dir();
        std::fs::create_dir_all(&data_dir)?;

        // Prefer uv-managed venv when present in dev.
        let python_exec = {
            let venv_python = root.join(".venv").join(if cfg!(target_os = "windows") {
                "Scripts/python.exe"
            } else {
                "bin/python"
            });
            if venv_python.exists() {
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

        let child = cmd
            .spawn()
            .with_context(|| format!("failed to spawn {:?}", python_exec))?;
        *self.child.lock().expect("process mutex") = Some(child);
        Ok(())
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
            if let Ok(resp) = client.get("http://127.0.0.1:8765/api/health").send().await {
                if resp.status().is_success() {
                    return Ok(());
                }
            }
            tokio::time::sleep(Duration::from_millis(300)).await;
        }
        Err(anyhow!("orchestrator health check timed out"))
    }

    pub fn python_root_display(&self) -> PathBuf {
        forge_python_root(None)
    }
}
