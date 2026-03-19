mod app;
mod manager;

use app::NanoclawDesktopApp;

fn main() -> eframe::Result<()> {
    let options = eframe::NativeOptions {
        viewport: eframe::egui::ViewportBuilder::default()
            .with_inner_size([960.0, 720.0])
            .with_min_inner_size([760.0, 560.0])
            .with_title("nanoclaw-mini Desktop"),
        ..Default::default()
    };

    eframe::run_native(
        "nanoclaw-mini Desktop",
        options,
        Box::new(|_cc| Ok(Box::new(NanoclawDesktopApp::new()))),
    )
}
