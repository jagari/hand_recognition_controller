// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

#[cfg(not(target_os = "windows"))]
use enigo::{Enigo, MouseControllable, MouseButton, KeyboardControllable, Key};
use tauri::Manager;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::{TrayIconBuilder, TrayIconEvent};
use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, Modifiers, Code, ShortcutState};

#[cfg(target_os = "windows")]
mod win_mouse {
    use std::mem::size_of;
    use windows_sys::Win32::UI::Input::KeyboardAndMouse::{
        SendInput, INPUT, INPUT_0, INPUT_MOUSE, MOUSEEVENTF_ABSOLUTE, MOUSEEVENTF_LEFTDOWN,
        MOUSEEVENTF_LEFTUP, MOUSEEVENTF_MOVE, MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP,
        MOUSEEVENTF_WHEEL, MOUSEINPUT,
    };
    use windows_sys::Win32::UI::WindowsAndMessaging::{GetSystemMetrics, SM_CXSCREEN, SM_CYSCREEN};

    fn send_mouse_input(dx: i32, dy: i32, flags: u32, mouse_data: u32) -> Result<(), String> {
        let mut input = INPUT {
            r#type: INPUT_MOUSE,
            Anonymous: INPUT_0 {
                mi: MOUSEINPUT {
                    dx,
                    dy,
                    mouseData: mouse_data,
                    dwFlags: flags,
                    time: 0,
                    dwExtraInfo: 0,
                },
            },
        };

        let sent = unsafe { SendInput(1, &mut input, size_of::<INPUT>() as i32) };
        if sent == 1 {
            Ok(())
        } else {
            Err("SendInput failed".to_string())
        }
    }

    pub fn win_move_mouse(x: i32, y: i32) {
        let width = unsafe { GetSystemMetrics(SM_CXSCREEN) };
        let height = unsafe { GetSystemMetrics(SM_CYSCREEN) };
        if width <= 1 || height <= 1 {
            return;
        }

        let normalized_x = (x.clamp(0, width - 1) * 65_535) / (width - 1);
        let normalized_y = (y.clamp(0, height - 1) * 65_535) / (height - 1);
        let _ = send_mouse_input(normalized_x, normalized_y, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0);
    }

    pub fn win_click_mouse(button: String, count: i32) {
        let (down_flag, up_flag) = match button.as_str() {
            "right" => (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
            _ => (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
        };

        for _ in 0..count {
            let _ = send_mouse_input(0, 0, down_flag, 0);
            let _ = send_mouse_input(0, 0, up_flag, 0);
        }
    }

    pub fn win_set_drag(button: String, is_dragging: bool) {
        let flag = match button.as_str() {
            "right" => {
                if is_dragging { MOUSEEVENTF_RIGHTDOWN } else { MOUSEEVENTF_RIGHTUP }
            }
            _ => {
                if is_dragging { MOUSEEVENTF_LEFTDOWN } else { MOUSEEVENTF_LEFTUP }
            }
        };
        let _ = send_mouse_input(0, 0, flag, 0);
    }

    pub fn win_scroll_mouse(dy: i32) {
        const WHEEL_DELTA: i32 = 120;
        if dy == 0 {
            return;
        }

        let _ = send_mouse_input(
            0,
            0,
            MOUSEEVENTF_WHEEL,
            (dy * WHEEL_DELTA) as u32,
        );
    }
}

#[tauri::command]
fn move_mouse(x: i32, y: i32) {
    #[cfg(target_os = "windows")]
    {
        win_mouse::win_move_mouse(x, y);
    }
    #[cfg(not(target_os = "windows"))]
    {
        let mut enigo = Enigo::new();
        enigo.mouse_move_to(x, y);
    }
}

#[tauri::command]
fn click_mouse(button: String, count: i32) {
    #[cfg(target_os = "windows")]
    {
        win_mouse::win_click_mouse(button, count);
    }
    #[cfg(not(target_os = "windows"))]
    {
        let mut enigo = Enigo::new();
        let b = match button.as_str() {
            "right" => MouseButton::Right,
            _ => MouseButton::Left,
        };
        
        for _ in 0..count {
            enigo.mouse_click(b);
        }
    }
}

#[tauri::command]
fn set_drag(button: String, is_dragging: bool) {
    #[cfg(target_os = "windows")]
    {
        win_mouse::win_set_drag(button, is_dragging);
    }
    #[cfg(not(target_os = "windows"))]
    {
        let mut enigo = Enigo::new();
        let b = match button.as_str() {
            "right" => MouseButton::Right,
            _ => MouseButton::Left,
        };

        if is_dragging {
            enigo.mouse_down(b);
        } else {
            enigo.mouse_up(b);
        }
    }
}

#[tauri::command]
fn scroll_mouse(dy: i32) {
    println!("[Rust] scroll_mouse called: dy={}", dy);
    #[cfg(target_os = "windows")]
    {
        win_mouse::win_scroll_mouse(dy);
    }
    #[cfg(not(target_os = "windows"))]
    {
        let mut enigo = Enigo::new();
        enigo.mouse_scroll_y(dy * 3);
    }
}

#[tauri::command]
fn trigger_mission_control() {
    #[cfg(target_os = "macos")]
    {
        let mut enigo = Enigo::new();
        enigo.key_down(Key::Control);
        enigo.key_click(Key::UpArrow);
        enigo.key_up(Key::Control);
    }
}

#[tauri::command]
fn save_config(config_json: String) -> Result<(), String> {
    use std::fs::File;
    use std::io::Write;
    let mut file = File::create("config.json").map_err(|e| e.to_string())?;
    file.write_all(config_json.as_bytes()).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn load_config() -> Option<String> {
    use std::fs::File;
    use std::io::Read;
    let mut file = File::open("config.json").ok()?;
    let mut contents = String::new();
    file.read_to_string(&mut contents).ok()?;
    Some(contents)
}

fn main() {
    let shortcut_plugin = tauri_plugin_global_shortcut::Builder::new()
        .with_handler(|app, _shortcut, event| {
            if event.state() == ShortcutState::Pressed {
                if let Some(window) = app.get_webview_window("main") {
                    let visible = window.is_visible().unwrap_or(false);
                    if visible {
                        let _ = window.hide();
                    } else {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
            }
        })
        .build();

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(shortcut_plugin)
        .setup(|app| {
            // macOS 환경에서 앱 기동 시 모든 가상 데스크톱(Spaces)에 창이 연동되도록 강제 설정합니다.
            #[cfg(target_os = "macos")]
            for window in app.webview_windows().values() {
                let _ = window.set_visible_on_all_workspaces(true);
            }

            // 전역 단축키 등록
            let ctrl_shift_h = Shortcut::new(
                Some(Modifiers::CONTROL | Modifiers::SHIFT),
                Code::KeyH,
            );
            let cmd_shift_h = Shortcut::new(
                Some(Modifiers::SUPER | Modifiers::SHIFT),
                Code::KeyH,
            );
            let _ = app.global_shortcut().register(ctrl_shift_h);
            let _ = app.global_shortcut().register(cmd_shift_h);

            // 시스템 트레이 구축 (Menu & Actions)
            let show_item = MenuItem::with_id(app, "show", "앱 열기 (Show Window)", true, None::<&str>)?;
            let hide_item = MenuItem::with_id(app, "hide", "앱 숨기기 (Hide Window)", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "앱 종료 (Quit)", true, None::<&str>)?;
            let tray_menu = Menu::with_items(app, &[&show_item, &hide_item, &quit_item])?;

            let mut tray_builder = TrayIconBuilder::new().menu(&tray_menu);
            if let Some(icon) = app.default_window_icon() {
                tray_builder = tray_builder.icon(icon.clone());
            }

            let _tray = tray_builder
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "hide" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.hide();
                        }
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click { button_state: _, .. } = event {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let visible = window.is_visible().unwrap_or(false);
                            if visible {
                                let _ = window.hide();
                            } else {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                    }
                })
                .build(app)?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            move_mouse, 
            click_mouse, 
            set_drag,
            scroll_mouse,
            trigger_mission_control,
            save_config,
            load_config
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
