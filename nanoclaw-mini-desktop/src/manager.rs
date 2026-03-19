use std::env;
use std::fmt::Write as _;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use anyhow::{anyhow, Context, Result};
use directories::BaseDirs;

pub const REPO_URL: &str = "https://github.com/lengff123/nanoclaw-mini";
pub const DEFAULT_BRANCH: &str = "main";
const AUTOSTART_NAME: &str = "nanoclaw-mini-desktop";
const RUN_KEY: &str = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run";
const MAC_LAUNCH_AGENT_LABEL: &str = "com.nanoclaw-mini.desktop";

#[derive(Clone, Debug)]
pub struct InstallState {
    pub install_dir: PathBuf,
    pub exists: bool,
    pub looks_like_repo: bool,
    pub git_available: bool,
    pub python_available: bool,
    pub local_commit: Option<String>,
    pub remote_commit: Option<String>,
    pub update_available: bool,
    pub autostart_supported: bool,
    pub autostart_enabled: bool,
}

impl InstallState {
    pub fn new(install_dir: PathBuf) -> Self {
        Self {
            install_dir,
            exists: false,
            looks_like_repo: false,
            git_available: false,
            python_available: false,
            local_commit: None,
            remote_commit: None,
            update_available: false,
            autostart_supported: cfg!(target_os = "windows") || cfg!(target_os = "macos"),
            autostart_enabled: false,
        }
    }

    pub fn installed(&self) -> bool {
        self.exists && self.looks_like_repo
    }
}

#[derive(Clone, Debug)]
pub struct ActionOutcome {
    pub state: InstallState,
    pub message: String,
    pub log: String,
}

#[derive(Clone, Debug)]
pub struct ManagerConfig {
    pub repo_url: String,
    pub branch: String,
}

impl Default for ManagerConfig {
    fn default() -> Self {
        Self {
            repo_url: REPO_URL.to_string(),
            branch: DEFAULT_BRANCH.to_string(),
        }
    }
}

#[derive(Clone, Debug)]
struct PythonInvocation {
    program: String,
    prefix_args: Vec<String>,
}

impl PythonInvocation {
    fn display(&self) -> String {
        if self.prefix_args.is_empty() {
            self.program.clone()
        } else {
            format!("{} {}", self.program, self.prefix_args.join(" "))
        }
    }
}

pub fn default_install_dir() -> PathBuf {
    let base = BaseDirs::new()
        .map(|dirs| dirs.data_local_dir().to_path_buf())
        .unwrap_or_else(env::temp_dir);
    base.join("nanoclaw-mini").join("managed-repo")
}

pub fn inspect(install_dir: &Path, config: &ManagerConfig) -> InstallState {
    let mut state = InstallState::new(install_dir.to_path_buf());
    state.git_available = command_exists("git");
    state.python_available = python_invocation().is_ok();
    state.exists = install_dir.exists();
    state.looks_like_repo =
        install_dir.join(".git").exists() && install_dir.join("pyproject.toml").exists();
    state.autostart_enabled = is_autostart_enabled().unwrap_or(false);

    if state.git_available {
        state.remote_commit = remote_head(config).ok();
    }

    if state.looks_like_repo && state.git_available {
        state.local_commit = local_head(install_dir).ok();
    }

    if let (Some(local), Some(remote)) = (&state.local_commit, &state.remote_commit) {
        state.update_available = local != remote;
    }

    state
}

pub fn install(install_dir: &Path, config: &ManagerConfig) -> Result<ActionOutcome> {
    let mut log = String::new();

    if install_dir.exists() && !looks_like_repo(install_dir) {
        return Err(anyhow!(
            "Installation path exists but is not a nanoclaw-mini repository: {}",
            install_dir.display()
        ));
    }

    require_command("git")?;
    let python = python_invocation()?;
    fs::create_dir_all(
        install_dir
            .parent()
            .ok_or_else(|| anyhow!("Invalid installation path: {}", install_dir.display()))?,
    )?;

    if !install_dir.exists() {
        let args = vec![
            "clone".to_string(),
            "--branch".to_string(),
            config.branch.clone(),
            config.repo_url.clone(),
            install_dir.display().to_string(),
        ];
        run_command("git", &args, None, &mut log).context("Failed to clone repository")?;
    } else {
        writeln!(
            &mut log,
            "Repository already exists at {}. Skipping clone.",
            install_dir.display()
        )
        .ok();
    }

    pip_install_editable(&python, install_dir, &mut log)?;

    Ok(ActionOutcome {
        state: inspect(install_dir, config),
        message: "nanoclaw-mini installed successfully.".to_string(),
        log,
    })
}

pub fn check_updates(install_dir: &Path, config: &ManagerConfig) -> Result<ActionOutcome> {
    let state = inspect(install_dir, config);
    let message = if !state.installed() {
        "nanoclaw-mini is not installed yet.".to_string()
    } else if state.update_available {
        "A newer commit is available.".to_string()
    } else {
        "Repository is already up to date.".to_string()
    };

    Ok(ActionOutcome {
        state,
        message,
        log: String::new(),
    })
}

pub fn update(install_dir: &Path, config: &ManagerConfig) -> Result<ActionOutcome> {
    if !looks_like_repo(install_dir) {
        return Err(anyhow!(
            "nanoclaw-mini is not installed at {}",
            install_dir.display()
        ));
    }

    let mut log = String::new();
    require_command("git")?;
    let python = python_invocation()?;

    let args = vec![
        "-C".to_string(),
        install_dir.display().to_string(),
        "pull".to_string(),
        "--ff-only".to_string(),
        "origin".to_string(),
        config.branch.clone(),
    ];
    run_command("git", &args, None, &mut log).context("Failed to update repository")?;

    pip_install_editable(&python, install_dir, &mut log)?;

    Ok(ActionOutcome {
        state: inspect(install_dir, config),
        message: "nanoclaw-mini updated successfully.".to_string(),
        log,
    })
}

pub fn uninstall(install_dir: &Path, config: &ManagerConfig) -> Result<ActionOutcome> {
    let mut log = String::new();
    let python = python_invocation();

    if install_dir.exists() {
        fs::remove_dir_all(install_dir)
            .with_context(|| format!("Failed to remove {}", install_dir.display()))?;
        writeln!(&mut log, "Removed repository at {}", install_dir.display()).ok();
    } else {
        writeln!(&mut log, "Installation path did not exist.").ok();
    }

    if let Ok(python) = python {
        let args = join_args(
            &python.prefix_args,
            &["-m", "pip", "uninstall", "-y", "nanoclaw-mini"],
        );
        let _ = run_command(&python.program, &args, None, &mut log);
    }

    let _ = disable_autostart();

    Ok(ActionOutcome {
        state: inspect(install_dir, config),
        message: "nanoclaw-mini uninstalled.".to_string(),
        log,
    })
}

pub fn open_install_dir(install_dir: &Path) -> Result<String> {
    if !install_dir.exists() {
        return Err(anyhow!(
            "Install directory does not exist: {}",
            install_dir.display()
        ));
    }

    if cfg!(target_os = "windows") {
        Command::new("explorer")
            .arg(install_dir)
            .spawn()
            .context("Failed to open Explorer")?;
    } else if cfg!(target_os = "macos") {
        Command::new("open")
            .arg(install_dir)
            .spawn()
            .context("Failed to open Finder")?;
    } else {
        Command::new("xdg-open")
            .arg(install_dir)
            .spawn()
            .context("Failed to open file manager")?;
    }

    Ok(format!("Opened {}", install_dir.display()))
}

pub fn set_autostart(enabled: bool) -> Result<String> {
    if enabled {
        enable_autostart()?;
        Ok("Autostart enabled.".to_string())
    } else {
        disable_autostart()?;
        Ok("Autostart disabled.".to_string())
    }
}

pub fn initialize(install_dir: &Path) -> Result<String> {
    launch_cli_terminal(install_dir, &["onboard"], "nanoclaw-mini Initialize")?;
    Ok("Opened a terminal window for nanoclaw-mini initialization.".to_string())
}

pub fn login_codex(install_dir: &Path) -> Result<String> {
    launch_cli_terminal(
        install_dir,
        &["provider", "login", "codex"],
        "nanoclaw-mini Codex Login",
    )?;
    Ok("Opened a terminal window for Codex login.".to_string())
}

pub fn launch_agent(install_dir: &Path) -> Result<String> {
    launch_cli_terminal(install_dir, &["agent"], "nanoclaw-mini Agent")?;
    Ok("Opened a terminal window for the interactive agent.".to_string())
}

pub fn is_autostart_enabled() -> Result<bool> {
    if cfg!(target_os = "windows") {
        let output = Command::new("reg")
            .args(["query", RUN_KEY, "/v", AUTOSTART_NAME])
            .output()
            .context("Failed to query autostart registry")?;
        return Ok(output.status.success());
    }

    if cfg!(target_os = "macos") {
        return Ok(macos_launch_agent_path()?.exists());
    }

    Ok(false)
}

fn enable_autostart() -> Result<()> {
    if cfg!(target_os = "windows") {
        let exe = env::current_exe().context("Failed to get current executable path")?;
        let value = format!("\"{}\"", exe.display());

        let status = Command::new("reg")
            .args([
                "add",
                RUN_KEY,
                "/v",
                AUTOSTART_NAME,
                "/t",
                "REG_SZ",
                "/d",
                &value,
                "/f",
            ])
            .status()
            .context("Failed to write autostart registry key")?;

        if status.success() {
            return Ok(());
        }

        return Err(anyhow!("Failed to enable autostart."));
    }

    if cfg!(target_os = "macos") {
        return enable_macos_autostart();
    }

    Err(anyhow!(
        "Autostart is currently implemented for Windows and macOS only."
    ))
}

fn disable_autostart() -> Result<()> {
    if cfg!(target_os = "windows") {
        let status = Command::new("reg")
            .args(["delete", RUN_KEY, "/v", AUTOSTART_NAME, "/f"])
            .status()
            .context("Failed to delete autostart registry key")?;

        if status.success() {
            return Ok(());
        }

        return Err(anyhow!("Failed to disable autostart."));
    }

    if cfg!(target_os = "macos") {
        return disable_macos_autostart();
    }

    Ok(())
}

fn enable_macos_autostart() -> Result<()> {
    let exe = env::current_exe().context("Failed to get current executable path")?;
    let plist_path = macos_launch_agent_path()?;
    let plist_parent = plist_path
        .parent()
        .ok_or_else(|| anyhow!("Invalid LaunchAgents path: {}", plist_path.display()))?;
    fs::create_dir_all(plist_parent)?;

    let plist = format!(
        r#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{program}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <false/>
</dict>
</plist>
"#,
        label = xml_escape(MAC_LAUNCH_AGENT_LABEL),
        program = xml_escape(&exe.to_string_lossy()),
    );
    fs::write(&plist_path, plist)
        .with_context(|| format!("Failed to write {}", plist_path.display()))?;

    let plist_arg = plist_path.display().to_string();
    let _ = Command::new("launchctl")
        .args(["unload", &plist_arg])
        .status();
    let status = Command::new("launchctl")
        .args(["load", &plist_arg])
        .status()
        .context("Failed to load LaunchAgent")?;

    if status.success() {
        return Ok(());
    }

    Err(anyhow!("Failed to enable autostart via launchctl."))
}

fn disable_macos_autostart() -> Result<()> {
    let plist_path = macos_launch_agent_path()?;
    let plist_arg = plist_path.display().to_string();

    if plist_path.exists() {
        let _ = Command::new("launchctl")
            .args(["unload", &plist_arg])
            .status();
        fs::remove_file(&plist_path)
            .with_context(|| format!("Failed to remove {}", plist_path.display()))?;
    }

    Ok(())
}

fn looks_like_repo(path: &Path) -> bool {
    path.join(".git").exists() && path.join("pyproject.toml").exists()
}

fn launch_cli_terminal(install_dir: &Path, cli_args: &[&str], title: &str) -> Result<()> {
    if !looks_like_repo(install_dir) {
        return Err(anyhow!(
            "nanoclaw-mini is not installed at {}",
            install_dir.display()
        ));
    }

    let python = python_invocation()?;

    if cfg!(target_os = "windows") {
        launch_windows_terminal(install_dir, &python, cli_args, title)
    } else if cfg!(target_os = "macos") {
        launch_macos_terminal(install_dir, &python, cli_args)
    } else {
        Err(anyhow!(
            "Quick launch actions are currently implemented for Windows and macOS only."
        ))
    }
}

fn launch_windows_terminal(
    install_dir: &Path,
    python: &PythonInvocation,
    cli_args: &[&str],
    title: &str,
) -> Result<()> {
    let command_string = python_module_command_string(python, cli_args);

    Command::new("cmd")
        .current_dir(install_dir)
        .env("PYTHONIOENCODING", "utf-8")
        .env("PYTHONUTF8", "1")
        .args(["/C", "start", title, "cmd", "/K", &command_string])
        .spawn()
        .with_context(|| format!("Failed to open terminal for {}", command_string))?;

    Ok(())
}

fn launch_macos_terminal(
    install_dir: &Path,
    python: &PythonInvocation,
    cli_args: &[&str],
) -> Result<()> {
    let shell_command = format!(
        "cd {} && export PYTHONIOENCODING=utf-8 PYTHONUTF8=1 && {}",
        sh_arg(&install_dir.display().to_string()),
        shell_command_string(python, cli_args),
    );
    let script = format!(
        "tell application \"Terminal\"\nactivate\ndo script \"{}\"\nend tell",
        applescript_escape(&shell_command),
    );

    Command::new("osascript")
        .arg("-e")
        .arg(script)
        .spawn()
        .context("Failed to open Terminal.app")?;

    Ok(())
}

fn python_module_command_string(python: &PythonInvocation, cli_args: &[&str]) -> String {
    let mut parts = Vec::new();
    parts.push(cmd_arg(&python.program));
    parts.extend(python.prefix_args.iter().map(|arg| cmd_arg(arg)));
    parts.push("-m".to_string());
    parts.push("nanoclaw_mini".to_string());
    parts.extend(cli_args.iter().map(|arg| cmd_arg(arg)));
    parts.join(" ")
}

fn shell_command_string(python: &PythonInvocation, cli_args: &[&str]) -> String {
    let mut parts = Vec::new();
    parts.push(sh_arg(&python.program));
    parts.extend(python.prefix_args.iter().map(|arg| sh_arg(arg)));
    parts.push("-m".to_string());
    parts.push("nanoclaw_mini".to_string());
    parts.extend(cli_args.iter().map(|arg| sh_arg(arg)));
    parts.join(" ")
}

fn cmd_arg(value: &str) -> String {
    if value.is_empty() {
        return "\"\"".to_string();
    }

    if value.contains([' ', '\t', '"']) {
        format!("\"{}\"", value.replace('"', "\"\""))
    } else {
        value.to_string()
    }
}

fn sh_arg(value: &str) -> String {
    if value.is_empty() {
        return "''".to_string();
    }

    format!("'{}'", value.replace('\'', "'\"'\"'"))
}

fn applescript_escape(value: &str) -> String {
    value.replace('\\', "\\\\").replace('"', "\\\"")
}

fn xml_escape(value: &str) -> String {
    value
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&apos;")
}

fn macos_launch_agent_path() -> Result<PathBuf> {
    let base_dirs = BaseDirs::new().ok_or_else(|| anyhow!("Failed to locate home directory"))?;
    Ok(base_dirs
        .home_dir()
        .join("Library")
        .join("LaunchAgents")
        .join(format!("{MAC_LAUNCH_AGENT_LABEL}.plist")))
}

fn local_head(install_dir: &Path) -> Result<String> {
    run_capture(
        "git",
        &[
            "-C".to_string(),
            install_dir.display().to_string(),
            "rev-parse".to_string(),
            "HEAD".to_string(),
        ],
        None,
    )
}

fn remote_head(config: &ManagerConfig) -> Result<String> {
    let output = run_capture(
        "git",
        &[
            "ls-remote".to_string(),
            config.repo_url.clone(),
            format!("refs/heads/{}", config.branch),
        ],
        None,
    )?;
    output
        .split_whitespace()
        .next()
        .map(|s| s.to_string())
        .ok_or_else(|| anyhow!("Unable to parse remote commit hash"))
}

fn pip_install_editable(
    python: &PythonInvocation,
    install_dir: &Path,
    log: &mut String,
) -> Result<()> {
    writeln!(log, "Using Python launcher: {}", python.display()).ok();
    let args = join_args(&python.prefix_args, &["-m", "pip", "install", "-e", "."]);
    run_command(&python.program, &args, Some(install_dir), log)
        .context("Failed to install nanoclaw-mini with pip")
}

fn python_invocation() -> Result<PythonInvocation> {
    let candidates = [
        PythonInvocation {
            program: "python".to_string(),
            prefix_args: vec![],
        },
        PythonInvocation {
            program: "py".to_string(),
            prefix_args: vec!["-3".to_string()],
        },
        PythonInvocation {
            program: "py".to_string(),
            prefix_args: vec![],
        },
    ];

    for candidate in candidates {
        let version_args = join_args(&candidate.prefix_args, &["--version"]);
        if Command::new(&candidate.program)
            .args(&version_args)
            .output()
            .map(|output| output.status.success())
            .unwrap_or(false)
        {
            return Ok(candidate);
        }
    }

    Err(anyhow!(
        "Python was not found. Please install Python 3.11+ before continuing."
    ))
}

fn command_exists(program: &str) -> bool {
    Command::new(program)
        .arg("--version")
        .output()
        .map(|output| output.status.success())
        .unwrap_or(false)
}

fn require_command(program: &str) -> Result<()> {
    if command_exists(program) {
        Ok(())
    } else {
        Err(anyhow!("Required command not found in PATH: {program}"))
    }
}

fn run_capture(program: &str, args: &[String], cwd: Option<&Path>) -> Result<String> {
    let mut command = Command::new(program);
    command.args(args);
    if let Some(cwd) = cwd {
        command.current_dir(cwd);
    }

    let output = command
        .output()
        .with_context(|| format!("Failed to execute {}", command_preview(program, args)))?;

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
    } else {
        Err(anyhow!(
            "{}",
            failure_message(program, args, &output.stdout, &output.stderr)
        ))
    }
}

fn run_command(program: &str, args: &[String], cwd: Option<&Path>, log: &mut String) -> Result<()> {
    writeln!(log, "> {}", command_preview(program, args)).ok();

    let mut command = Command::new(program);
    command.args(args);
    if let Some(cwd) = cwd {
        command.current_dir(cwd);
        writeln!(log, "  cwd: {}", cwd.display()).ok();
    }

    let output = command
        .output()
        .with_context(|| format!("Failed to execute {}", command_preview(program, args)))?;

    if !output.stdout.is_empty() {
        writeln!(log, "{}", String::from_utf8_lossy(&output.stdout).trim()).ok();
    }
    if !output.stderr.is_empty() {
        writeln!(log, "{}", String::from_utf8_lossy(&output.stderr).trim()).ok();
    }
    writeln!(log, "Exit code: {}", output.status.code().unwrap_or(-1)).ok();
    writeln!(log).ok();

    if output.status.success() {
        Ok(())
    } else {
        Err(anyhow!(
            "{}",
            failure_message(program, args, &output.stdout, &output.stderr)
        ))
    }
}

fn failure_message(program: &str, args: &[String], stdout: &[u8], stderr: &[u8]) -> String {
    let mut message = format!("Command failed: {}", command_preview(program, args));
    let stdout_text = String::from_utf8_lossy(stdout).trim().to_string();
    let stderr_text = String::from_utf8_lossy(stderr).trim().to_string();
    if !stdout_text.is_empty() {
        message.push_str("\nstdout:\n");
        message.push_str(&stdout_text);
    }
    if !stderr_text.is_empty() {
        message.push_str("\nstderr:\n");
        message.push_str(&stderr_text);
    }
    message
}

fn command_preview(program: &str, args: &[String]) -> String {
    if args.is_empty() {
        program.to_string()
    } else {
        format!("{program} {}", args.join(" "))
    }
}

fn join_args(prefix: &[String], tail: &[&str]) -> Vec<String> {
    let mut args = prefix.to_vec();
    args.extend(tail.iter().map(|item| (*item).to_string()));
    args
}
