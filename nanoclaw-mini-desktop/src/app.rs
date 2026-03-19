use std::path::PathBuf;
use std::sync::mpsc::{self, Receiver};
use std::thread;

use eframe::egui::{self, Color32, RichText, TextEdit};

use crate::manager::{
    check_updates, default_install_dir, initialize, inspect, install, launch_agent, login_codex,
    open_install_dir, set_autostart, uninstall, update, ActionOutcome, InstallState, ManagerConfig,
    REPO_URL,
};

pub struct NanoclawDesktopApp {
    config: ManagerConfig,
    install_dir_input: String,
    state: InstallState,
    status: String,
    log: String,
    busy: bool,
    task_rx: Option<Receiver<TaskResult>>,
}

impl NanoclawDesktopApp {
    pub fn new() -> Self {
        let install_dir = default_install_dir();
        let config = ManagerConfig::default();
        let state = inspect(&install_dir, &config);
        let mut app = Self {
            config,
            install_dir_input: install_dir.display().to_string(),
            state,
            status: "Ready.".to_string(),
            log: String::new(),
            busy: false,
            task_rx: None,
        };
        app.spawn_task(Task::Refresh);
        app
    }

    fn install_dir(&self) -> PathBuf {
        PathBuf::from(self.install_dir_input.trim())
    }

    fn spawn_task(&mut self, task: Task) {
        if self.busy {
            return;
        }

        let install_dir = self.install_dir();
        let config = self.config.clone();
        let (tx, rx) = mpsc::channel();
        self.busy = true;
        self.task_rx = Some(rx);
        self.status = task.start_message().to_string();

        thread::spawn(move || {
            let result = match task {
                Task::Refresh => Ok(TaskOutput::Outcome(ActionOutcome {
                    state: inspect(&install_dir, &config),
                    message: "State refreshed.".to_string(),
                    log: String::new(),
                })),
                Task::Install => install(&install_dir, &config).map(TaskOutput::Outcome),
                Task::Initialize => initialize(&install_dir).map(TaskOutput::Message),
                Task::LoginCodex => login_codex(&install_dir).map(TaskOutput::Message),
                Task::LaunchAgent => launch_agent(&install_dir).map(TaskOutput::Message),
                Task::CheckUpdates => check_updates(&install_dir, &config).map(TaskOutput::Outcome),
                Task::Update => update(&install_dir, &config).map(TaskOutput::Outcome),
                Task::Uninstall => uninstall(&install_dir, &config).map(TaskOutput::Outcome),
                Task::SetAutostart(enabled) => set_autostart(enabled).map(TaskOutput::Message),
                Task::OpenInstallDir => open_install_dir(&install_dir).map(TaskOutput::Message),
            };

            let task_result = match result {
                Ok(output) => TaskResult::Success(output),
                Err(err) => TaskResult::Error(err.to_string()),
            };
            let _ = tx.send(task_result);
        });
    }

    fn poll_task(&mut self) {
        if let Some(rx) = &self.task_rx {
            if let Ok(result) = rx.try_recv() {
                self.busy = false;
                self.task_rx = None;
                match result {
                    TaskResult::Success(TaskOutput::Outcome(outcome)) => {
                        self.state = outcome.state;
                        self.status = outcome.message;
                        if !outcome.log.trim().is_empty() {
                            self.log = outcome.log;
                        }
                    }
                    TaskResult::Success(TaskOutput::Message(message)) => {
                        self.status = message;
                        self.state = inspect(&self.install_dir(), &self.config);
                    }
                    TaskResult::Error(message) => {
                        self.status = "Operation failed.".to_string();
                        if self.log.trim().is_empty() {
                            self.log.clear();
                        }
                        if !self.log.ends_with('\n') && !self.log.is_empty() {
                            self.log.push('\n');
                        }
                        self.log.push_str(&message);
                    }
                }
            }
        }
    }
}

impl eframe::App for NanoclawDesktopApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.poll_task();

        egui::TopBottomPanel::top("top").show(ctx, |ui| {
            ui.add_space(8.0);
            ui.heading("nanoclaw-mini Desktop");
            ui.label("Rust desktop manager for cloning, installing, updating, uninstalling, and auto-starting nanoclaw-mini.");
            ui.hyperlink_to("Repository", REPO_URL);
            ui.add_space(8.0);
        });

        egui::CentralPanel::default().show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.label("Install directory");
                ui.add_enabled(
                    !self.busy,
                    TextEdit::singleline(&mut self.install_dir_input).desired_width(f32::INFINITY),
                );
            });

            ui.add_space(8.0);
            ui.horizontal_wrapped(|ui| {
                if ui
                    .add_enabled(!self.busy, egui::Button::new("Check Exists"))
                    .clicked()
                {
                    self.spawn_task(Task::Refresh);
                }
                if ui
                    .add_enabled(!self.busy, egui::Button::new("Install"))
                    .clicked()
                {
                    self.spawn_task(Task::Install);
                }
                if ui
                    .add_enabled(
                        !self.busy && self.state.installed() && self.state.python_available,
                        egui::Button::new("Initialize"),
                    )
                    .clicked()
                {
                    self.spawn_task(Task::Initialize);
                }
                if ui
                    .add_enabled(
                        !self.busy && self.state.installed() && self.state.python_available,
                        egui::Button::new("Codex Login"),
                    )
                    .clicked()
                {
                    self.spawn_task(Task::LoginCodex);
                }
                if ui
                    .add_enabled(
                        !self.busy && self.state.installed() && self.state.python_available,
                        egui::Button::new("Launch Agent"),
                    )
                    .clicked()
                {
                    self.spawn_task(Task::LaunchAgent);
                }
                if ui
                    .add_enabled(
                        !self.busy && self.state.installed(),
                        egui::Button::new("Check Update"),
                    )
                    .clicked()
                {
                    self.spawn_task(Task::CheckUpdates);
                }
                if ui
                    .add_enabled(
                        !self.busy && self.state.installed() && self.state.update_available,
                        egui::Button::new("Update"),
                    )
                    .clicked()
                {
                    self.spawn_task(Task::Update);
                }
                if ui
                    .add_enabled(
                        !self.busy && self.state.exists,
                        egui::Button::new("Open Folder"),
                    )
                    .clicked()
                {
                    self.spawn_task(Task::OpenInstallDir);
                }
                if ui
                    .add_enabled(
                        !self.busy && self.state.exists,
                        egui::Button::new("Uninstall"),
                    )
                    .clicked()
                {
                    self.spawn_task(Task::Uninstall);
                }
            });

            ui.add_space(6.0);
            ui.label(
                RichText::new(
                    "Initialize, Codex Login, and Launch Agent open a separate terminal window.",
                )
                .color(Color32::GRAY),
            );
            ui.add_space(6.0);
            let autostart_label = if self.state.autostart_enabled {
                "Disable Autostart"
            } else {
                "Enable Autostart"
            };
            if ui
                .add_enabled(
                    !self.busy && self.state.autostart_supported,
                    egui::Button::new(autostart_label),
                )
                .clicked()
            {
                self.spawn_task(Task::SetAutostart(!self.state.autostart_enabled));
            }

            if !self.state.autostart_supported {
                ui.label(
                    RichText::new("Autostart is currently implemented for Windows only.")
                        .color(Color32::YELLOW),
                );
            }

            ui.separator();

            egui::Grid::new("status_grid")
                .num_columns(2)
                .spacing([24.0, 8.0])
                .show(ui, |ui| {
                    ui.label("Managed path");
                    ui.label(self.state.install_dir.display().to_string());
                    ui.end_row();

                    ui.label("Installed");
                    ui.label(if self.state.installed() { "Yes" } else { "No" });
                    ui.end_row();

                    ui.label("Git available");
                    ui.label(if self.state.git_available {
                        "Yes"
                    } else {
                        "No"
                    });
                    ui.end_row();

                    ui.label("Python available");
                    ui.label(if self.state.python_available {
                        "Yes"
                    } else {
                        "No"
                    });
                    ui.end_row();

                    ui.label("Autostart");
                    ui.label(if self.state.autostart_enabled {
                        "Enabled"
                    } else {
                        "Disabled"
                    });
                    ui.end_row();

                    ui.label("Local commit");
                    ui.label(self.state.local_commit.as_deref().unwrap_or("-"));
                    ui.end_row();

                    ui.label("Remote commit");
                    ui.label(self.state.remote_commit.as_deref().unwrap_or("-"));
                    ui.end_row();

                    ui.label("Update available");
                    ui.label(if self.state.update_available {
                        "Yes"
                    } else {
                        "No"
                    });
                    ui.end_row();
                });

            ui.add_space(10.0);
            if self.state.update_available {
                ui.colored_label(
                    Color32::YELLOW,
                    "A newer nanoclaw-mini version is available. Click Update to pull and reinstall it.",
                );
                ui.add_space(6.0);
            }
            if self.busy {
                ui.colored_label(Color32::LIGHT_BLUE, "Task running...");
            }
            ui.label(RichText::new(&self.status).strong());

            ui.add_space(10.0);
            ui.label(RichText::new("Command Log").strong());
            ui.add(
                TextEdit::multiline(&mut self.log)
                    .desired_rows(18)
                    .desired_width(f32::INFINITY)
                    .font(egui::TextStyle::Monospace)
                    .interactive(false),
            );
        });

        ctx.request_repaint_after(std::time::Duration::from_millis(200));
    }
}

#[derive(Clone, Copy)]
enum Task {
    Refresh,
    Install,
    Initialize,
    LoginCodex,
    LaunchAgent,
    CheckUpdates,
    Update,
    Uninstall,
    SetAutostart(bool),
    OpenInstallDir,
}

impl Task {
    fn start_message(self) -> &'static str {
        match self {
            Task::Refresh => "Refreshing state...",
            Task::Install => "Installing nanoclaw-mini...",
            Task::Initialize => "Opening initialization terminal...",
            Task::LoginCodex => "Opening Codex login terminal...",
            Task::LaunchAgent => "Opening agent terminal...",
            Task::CheckUpdates => "Checking for updates...",
            Task::Update => "Updating nanoclaw-mini...",
            Task::Uninstall => "Uninstalling nanoclaw-mini...",
            Task::SetAutostart(true) => "Enabling autostart...",
            Task::SetAutostart(false) => "Disabling autostart...",
            Task::OpenInstallDir => "Opening install directory...",
        }
    }
}

enum TaskOutput {
    Outcome(ActionOutcome),
    Message(String),
}

enum TaskResult {
    Success(TaskOutput),
    Error(String),
}
