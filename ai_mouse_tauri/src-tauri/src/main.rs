// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use enigo::{Enigo, MouseControllable, MouseButton, KeyboardControllable, Key};
use tauri::Manager;

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

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            // macOS 환경에서 앱 기동 시 모든 가상 데스크톱(Spaces)에 창이 연동되도록 강제 설정합니다.
            #[cfg(target_os = "macos")]
            for window in app.webview_windows().values() {
                let _ = window.set_visible_on_all_workspaces(true);
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            move_mouse, 
            click_mouse, 
            set_drag,
            scroll_mouse,
            trigger_mission_control
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
