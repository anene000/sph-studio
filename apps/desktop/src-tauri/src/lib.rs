// SPH Studio desktop shell (Tauri v2).
//
// U18: opens a WebView serving the statically-exported Next.js frontend
// (apps/web/out) and, in dev, points at http://localhost:3000.
//
// U19 (next): launch the PyInstaller-built FastAPI backend as a Tauri sidecar
// via tauri-plugin-shell, and shut it down on window close. Sketch:
//
//   use tauri_plugin_shell::ShellExt;
//   .plugin(tauri_plugin_shell::init())
//   .setup(|app| {
//       let sidecar = app.shell().sidecar("sph-backend")?;
//       let (_rx, _child) = sidecar.spawn()?;
//       Ok(())
//   })

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
