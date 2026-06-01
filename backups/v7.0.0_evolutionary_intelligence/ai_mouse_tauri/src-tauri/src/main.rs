// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use enigo::{Enigo, MouseControllable, MouseButton};

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

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            move_mouse, 
            click_mouse, 
            set_drag
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
