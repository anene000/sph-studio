// SPH Studio desktop shell (Tauri v2).
//
// U18: opens a WebView serving the statically-exported Next.js frontend (apps/web/out),
//      or http://localhost:3000 in dev.
// U19: launches the PyInstaller-built FastAPI backend as a sidecar ("sph-backend") and
//      terminates it on exit. Because a PyInstaller onefile spawns a child process, a
//      forced/crashed close can orphan the sidecar and leave it holding port 8000,
//      which then blocks the next launch. To be robust we (1) kill any stale sidecar on
//      startup and (2) kill the whole sph-backend tree on exit (not just the tracked
//      child). When the sidecar is not bundled (dev) we fall back to an external backend.
use std::process::Command;

use tauri::RunEvent;
use tauri_plugin_shell::ShellExt;

#[cfg(target_os = "windows")]
fn kill_stale_sidecars() {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    let _ = Command::new("taskkill")
        .args(["/IM", "sph-backend.exe", "/F", "/T"])
        .creation_flags(CREATE_NO_WINDOW)
        .status();
}

#[cfg(not(target_os = "windows"))]
fn kill_stale_sidecars() {
    let _ = Command::new("pkill").args(["-f", "sph-backend"]).status();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Clear any sidecar left behind by a previous crashed/force-closed session so the
    // fresh one can bind the port.
    kill_stale_sidecars();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            match app.shell().sidecar("sph-backend") {
                Ok(cmd) => match cmd.spawn() {
                    Ok((_rx, _child)) => println!("[sph-studio] backend sidecar started"),
                    Err(e) => eprintln!("[sph-studio] failed to spawn sidecar: {e}"),
                },
                Err(e) => eprintln!(
                    "[sph-studio] sidecar 'sph-backend' not bundled ({e}); \
                     expecting an externally started backend on 127.0.0.1:8000"
                ),
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|_app, event| {
            if let RunEvent::ExitRequested { .. } = event {
                kill_stale_sidecars();
            }
        });
}
