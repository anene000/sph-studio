// SPH Studio desktop shell (Tauri v2).
//
// U18: opens a WebView serving the statically-exported Next.js frontend (apps/web/out),
//      or http://localhost:3000 in dev.
// U19: launches the PyInstaller-built FastAPI backend as a sidecar ("sph-backend") and
//      terminates it on exit. The sidecar is only present in a fully bundled build
//      (after scripts/build_sidecar + adding bundle.externalBin); when it is absent
//      (dev, or a build without the sidecar) we fall back to an externally started
//      backend so the app still runs.
use std::sync::Mutex;

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

#[derive(Default)]
struct Sidecar(Mutex<Option<CommandChild>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(Sidecar::default())
        .setup(|app| {
            match app.shell().sidecar("sph-backend") {
                Ok(cmd) => match cmd.spawn() {
                    Ok((_rx, child)) => {
                        *app.state::<Sidecar>().0.lock().unwrap() = Some(child);
                        println!("[sph-studio] backend sidecar started");
                    }
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
        .run(|app, event| {
            if let RunEvent::ExitRequested { .. } = event {
                if let Some(child) = app.state::<Sidecar>().0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        });
}
