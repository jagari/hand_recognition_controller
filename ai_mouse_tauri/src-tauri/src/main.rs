// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use enigo::{Enigo, MouseControllable, MouseButton, KeyboardControllable, Key};
use tauri::Manager;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::{TrayIconBuilder, TrayIconEvent};
use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, Modifiers, Code, ShortcutState};

#[tauri::command]
fn move_mouse(x: i32, y: i32) {
    let mut enigo = Enigo::new();
    enigo.mouse_move_to(x, y);
}

#[tauri::command]
fn click_mouse(button: String, count: i32) {
    let mut enigo = Enigo::new();
    let b = match button.as_str() {
        "right" => MouseButton::Right,
        _ => MouseButton::Left,
    };
    
    for _ in 0..count {
        enigo.mouse_click(b);
    }
}

#[tauri::command]
fn set_drag(button: String, is_dragging: bool) {
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

#[tauri::command]
fn scroll_mouse(dy: i32) {
    #[cfg(target_os = "macos")]
    {
        use std::os::raw::c_void;
        type CGEventRef = *mut c_void;
        type CGEventSourceRef = *mut c_void;

        #[link(name = "CoreGraphics", kind = "framework")]
        extern "C" {
            fn CGEventCreateScrollWheelEvent(
                source: CGEventSourceRef,
                units: u32,
                wheelCount: u32,
                wheel1: i32,
                ...
            ) -> CGEventRef;
            fn CGEventPost(tap: u32, event: CGEventRef);
            fn CFRelease(obj: *mut c_void);
        }

        unsafe {
            // units: 1 = kCGScrollEventUnitLine (맥북 스크롤 인식을 위해 라인 단위로 복구)
            // 미세 스크롤 휠 가속 보완을 위해 3을 곱합니다.
            let scroll_lines = dy * 3;
            let event = CGEventCreateScrollWheelEvent(
                std::ptr::null_mut(),
                1, // kCGScrollEventUnitLine = 1
                1, // wheelCount = 1
                scroll_lines,
            );
            if !event.is_null() {
                // kCGSessionEventTap = 1 을 사용하여 Accessibility 권한 하에 전역 활성 세션에 정확히 마우스 휠 이벤트 주입
                CGEventPost(1, event); 
                CFRelease(event);
            }
        }
    }

    #[cfg(not(target_os = "macos"))]
    {
        let mut enigo = Enigo::new();
        enigo.mouse_scroll_y(dy);
    }
}

#[tauri::command]
fn trigger_mission_control() {
    let mut enigo = Enigo::new();
    enigo.key_down(Key::Control);
    enigo.key_click(Key::UpArrow);
    enigo.key_up(Key::Control);
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
