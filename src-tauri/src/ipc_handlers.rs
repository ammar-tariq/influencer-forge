use crate::process_manager::ProcessManager;
use serde::Serialize;
use std::sync::Arc;
use tauri::State;

#[derive(Serialize)]
pub struct BackendStatus {
    pub healthy: bool,
    pub message: String,
    pub data_dir: String,
    pub python_root: String,
}

#[tauri::command]
pub async fn backend_status(manager: State<'_, Arc<ProcessManager>>) -> Result<BackendStatus, String> {
    let healthy = reqwest::Client::new()
        .get("http://127.0.0.1:8765/api/health")
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false);
    Ok(BackendStatus {
        healthy,
        message: if healthy {
            "Orchestrator online".into()
        } else {
            "Orchestrator offline".into()
        },
        data_dir: crate::paths::app_data_dir().display().to_string(),
        python_root: manager.python_root_display().display().to_string(),
    })
}

#[tauri::command]
pub async fn restart_backend(manager: State<'_, Arc<ProcessManager>>) -> Result<BackendStatus, String> {
    manager.stop();
    manager
        .start_orchestrator()
        .map_err(|e| e.to_string())?;
    manager
        .wait_until_healthy(40)
        .await
        .map_err(|e| e.to_string())?;
    backend_status(manager).await
}
