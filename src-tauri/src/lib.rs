mod ipc_handlers;
mod paths;
mod process_manager;
mod system_tray;

use process_manager::ProcessManager;
use std::sync::Arc;
use tauri::{Emitter, RunEvent};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let manager = Arc::new(ProcessManager::default());
    let manager_for_setup = manager.clone();
    let manager_for_exit = manager.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(manager)
        .invoke_handler(tauri::generate_handler![
            ipc_handlers::backend_status,
            ipc_handlers::restart_backend
        ])
        .setup(move |app| {
            let handle = app.handle().clone();
            if let Err(err) = system_tray::build_tray(&handle) {
                eprintln!("tray unavailable: {err}");
            }
            let mgr = manager_for_setup.clone();
            tauri::async_runtime::spawn(async move {
                if let Err(err) = mgr.start_orchestrator() {
                    eprintln!("failed to start orchestrator: {err}");
                    let _ = handle.emit("backend-status", format!("error:{err}"));
                    return;
                }
                match mgr.wait_until_healthy(50).await {
                    Ok(()) => {
                        let _ = handle.emit("backend-status", "ready");
                    }
                    Err(err) => {
                        let _ = handle.emit("backend-status", format!("error:{err}"));
                    }
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building InfluencerForge")
        .run(move |_app_handle, event| {
            if let RunEvent::Exit = event {
                manager_for_exit.stop();
            }
        });
}
