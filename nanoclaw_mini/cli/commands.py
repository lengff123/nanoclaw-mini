"""CLI commands for nanoclaw-mini."""

import asyncio
import json
import os
import select
import signal
import sys
from pathlib import Path
from typing import Any

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    if sys.stdout.encoding != "utf-8":
        os.environ["PYTHONIOENCODING"] = "utf-8"
        # Re-open stdout/stderr with UTF-8 encoding
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import typer
from prompt_toolkit import print_formatted_text
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import ANSI, HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.application import run_in_terminal
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text

from nanoclaw_mini import __logo__, __version__
from nanoclaw_mini.config.paths import get_workspace_path
from nanoclaw_mini.config.schema import Config
from nanoclaw_mini.utils.helpers import sync_workspace_templates

app = typer.Typer(
    name="nanoclaw-mini",
    help=f"{__logo__} nanoclaw-mini - Personal AI Infrastructure",
    no_args_is_help=True,
)

console = Console()
EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit", ":q"}

# ---------------------------------------------------------------------------
# CLI input: prompt_toolkit for editing, paste, history, and display
# ---------------------------------------------------------------------------

_PROMPT_SESSION: PromptSession | None = None
_SAVED_TERM_ATTRS = None  # original termios settings, restored on exit


def _flush_pending_tty_input() -> None:
    """Drop unread keypresses typed while the model was generating output."""
    try:
        fd = sys.stdin.fileno()
        if not os.isatty(fd):
            return
    except Exception:
        return

    try:
        import termios
        termios.tcflush(fd, termios.TCIFLUSH)
        return
    except Exception:
        pass

    try:
        while True:
            ready, _, _ = select.select([fd], [], [], 0)
            if not ready:
                break
            if not os.read(fd, 4096):
                break
    except Exception:
        return


def _restore_terminal() -> None:
    """Restore terminal to its original state (echo, line buffering, etc.)."""
    if _SAVED_TERM_ATTRS is None:
        return
    try:
        import termios
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _SAVED_TERM_ATTRS)
    except Exception:
        pass


def _init_prompt_session() -> None:
    """Create the prompt_toolkit session with persistent file history."""
    global _PROMPT_SESSION, _SAVED_TERM_ATTRS

    # Save terminal state so we can restore it on exit
    try:
        import termios
        _SAVED_TERM_ATTRS = termios.tcgetattr(sys.stdin.fileno())
    except Exception:
        pass

    from nanoclaw_mini.config.paths import get_cli_history_path

    history_file = get_cli_history_path()
    history_file.parent.mkdir(parents=True, exist_ok=True)

    _PROMPT_SESSION = PromptSession(
        history=FileHistory(str(history_file)),
        enable_open_in_editor=False,
        multiline=False,   # Enter submits (single line mode)
    )


def _make_console() -> Console:
    return Console(file=sys.stdout)


def _render_interactive_ansi(render_fn) -> str:
    """Render Rich output to ANSI so prompt_toolkit can print it safely."""
    ansi_console = Console(
        force_terminal=True,
        color_system=console.color_system or "standard",
        width=console.width,
    )
    with ansi_console.capture() as capture:
        render_fn(ansi_console)
    return capture.get()


def _print_agent_response(response: str, render_markdown: bool) -> None:
    """Render assistant response with consistent terminal styling."""
    console = _make_console()
    content = response or ""
    body = Markdown(content) if render_markdown else Text(content)
    console.print()
    console.print(f"[cyan]{__logo__} nanoclaw-mini[/cyan]")
    console.print(body)
    console.print()


async def _print_interactive_line(text: str) -> None:
    """Print async interactive updates with prompt_toolkit-safe Rich styling."""
    def _write() -> None:
        ansi = _render_interactive_ansi(
            lambda c: c.print(f"  [dim]↳ {text}[/dim]")
        )
        print_formatted_text(ANSI(ansi), end="")

    await run_in_terminal(_write)


async def _print_interactive_response(response: str, render_markdown: bool) -> None:
    """Print async interactive replies with prompt_toolkit-safe Rich styling."""
    def _write() -> None:
        content = response or ""
        ansi = _render_interactive_ansi(
            lambda c: (
                c.print(),
                c.print(f"[cyan]{__logo__} nanoclaw-mini[/cyan]"),
                c.print(Markdown(content) if render_markdown else Text(content)),
                c.print(),
            )
        )
        print_formatted_text(ANSI(ansi), end="")

    await run_in_terminal(_write)


def _is_exit_command(command: str) -> bool:
    """Return True when input should end interactive chat."""
    return command.lower() in EXIT_COMMANDS


async def _read_interactive_input_async() -> str:
    """Read user input using prompt_toolkit (handles paste, history, display).

    prompt_toolkit natively handles:
    - Multiline paste (bracketed paste mode)
    - History navigation (up/down arrows)
    - Clean display (no ghost characters or artifacts)
    """
    if _PROMPT_SESSION is None:
        raise RuntimeError("Call _init_prompt_session() first")
    try:
        with patch_stdout():
            return await _PROMPT_SESSION.prompt_async(
                HTML("<b fg='ansiblue'>You:</b> "),
            )
    except EOFError as exc:
        raise KeyboardInterrupt from exc



def version_callback(value: bool):
    if value:
        console.print(f"{__logo__} nanoclaw-mini v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True
    ),
):
    """nanoclaw-mini - Personal AI Infrastructure."""
    pass


# ============================================================================
# Onboard / Setup
# ============================================================================


@app.command()
def onboard():
    """Initialize nanoclaw-mini configuration and workspace."""
    from nanoclaw_mini.config.loader import get_config_path, load_config, save_config
    from nanoclaw_mini.config.schema import Config

    config_path = get_config_path()

    if config_path.exists():
        console.print(f"[yellow]Config already exists at {config_path}[/yellow]")
        console.print("  [bold]y[/bold] = overwrite with defaults (existing values will be lost)")
        console.print("  [bold]N[/bold] = refresh config, keeping existing values and adding new fields")
        if typer.confirm("Overwrite?"):
            config = Config()
            save_config(config)
            console.print(f"[green]✓[/green] Config reset to defaults at {config_path}")
        else:
            config = load_config()
            save_config(config)
            console.print(f"[green]✓[/green] Config refreshed at {config_path} (existing values preserved)")
    else:
        save_config(Config())
        console.print(f"[green]✓[/green] Created config at {config_path}")

    console.print("[dim]Config template now uses `maxTokens` + `contextWindowTokens`; `memoryWindow` is no longer a runtime setting.[/dim]")

    # Create workspace
    workspace = get_workspace_path()

    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Created workspace at {workspace}")

    sync_workspace_templates(workspace)

    console.print(f"\n{__logo__} nanoclaw-mini is ready!")
    console.print("\nNext steps:")
    console.print("  1. Login with Codex: [cyan]nanoclaw-mini provider login codex[/cyan]")
    console.print("  2. Chat locally: [cyan]nanoclaw-mini agent -m \"Hello!\"[/cyan]")
    console.print("  3. Optional background tasks: [cyan]nanoclaw-mini gateway[/cyan]")


def _make_provider(config: Config):
    """Create the Codex OAuth provider."""
    from nanoclaw_mini.providers.base import GenerationSettings
    from nanoclaw_mini.providers.openai_codex_provider import OpenAICodexProvider

    model = config.agents.defaults.model
    provider = OpenAICodexProvider(default_model=model)

    defaults = config.agents.defaults
    provider.generation = GenerationSettings(
        temperature=defaults.temperature,
        max_tokens=defaults.max_tokens,
        reasoning_effort=defaults.reasoning_effort,
    )
    return provider


def _load_runtime_config(config: str | None = None, workspace: str | None = None) -> Config:
    """Load config and optionally override the active workspace."""
    from nanoclaw_mini.config.loader import load_config, set_config_path

    config_path = None
    if config:
        config_path = Path(config).expanduser().resolve()
        if not config_path.exists():
            console.print(f"[red]Error: Config file not found: {config_path}[/red]")
            raise typer.Exit(1)
        set_config_path(config_path)
        console.print(f"[dim]Using config: {config_path}[/dim]")

    loaded = load_config(config_path)
    if workspace:
        loaded.agents.defaults.workspace = workspace
    return loaded


def _load_editable_config(config: str | None = None) -> tuple[Config, Path]:
    """Load config for read/write commands and return its effective path."""
    from nanoclaw_mini.config.loader import get_config_path, load_config, set_config_path

    config_path = None
    if config:
        config_path = Path(config).expanduser().resolve()
        set_config_path(config_path)

    loaded = load_config(config_path)
    return loaded, get_config_path()


def _normalize_codex_model(model: str) -> str:
    """Accept bare slugs and normalize them to the configured model format."""
    normalized = model.strip()
    if not normalized:
        raise typer.BadParameter("Model name cannot be empty.")
    if normalized.startswith("openai_codex/"):
        return "openai-codex/" + normalized.split("/", 1)[1]
    if normalized.startswith("openai-codex/"):
        return normalized
    return f"openai-codex/{normalized}"


def _short_context_window(value: int | None) -> str:
    if value is None:
        return "-"
    if value >= 1000 and value % 1000 == 0:
        return f"{value // 1000}k"
    return str(value)


def _current_model_matches(current_model: str, candidate_id: str, candidate_slug: str) -> bool:
    current = _normalize_codex_model(current_model)
    return current == candidate_id or current.endswith("/" + candidate_slug)


def _print_deprecated_memory_window_notice(config: Config) -> None:
    """Warn when running with old memoryWindow-only config."""
    if config.agents.defaults.should_warn_deprecated_memory_window:
        console.print(
            "[yellow]Hint:[/yellow] Detected deprecated `memoryWindow` without "
            "`contextWindowTokens`. `memoryWindow` is ignored; run "
            "[cyan]nanoclaw-mini onboard[/cyan] to refresh your config template."
        )


# ============================================================================
# Gateway / Server
# ============================================================================


@app.command()
def gateway(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Start the background gateway for cron and heartbeat tasks."""
    from nanoclaw_mini.agent.loop import AgentLoop
    from nanoclaw_mini.agent.tools.message import MessageTool
    from nanoclaw_mini.bus.queue import MessageBus
    from nanoclaw_mini.config.paths import get_cron_dir
    from nanoclaw_mini.cron.service import CronService
    from nanoclaw_mini.cron.types import CronJob
    from nanoclaw_mini.heartbeat.service import HeartbeatService
    from nanoclaw_mini.session.manager import SessionManager

    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    config = _load_runtime_config(config, workspace)
    _print_deprecated_memory_window_notice(config)

    console.print(f"{__logo__} Starting nanoclaw-mini background gateway...")
    sync_workspace_templates(config.workspace_path)
    bus = MessageBus()
    provider = _make_provider(config)
    session_manager = SessionManager(config.workspace_path)

    # Create cron service first (callback set after agent creation)
    cron_store_path = get_cron_dir() / "jobs.json"
    cron = CronService(cron_store_path)

    # Create agent with cron service
    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=config.agents.defaults.model,
        max_iterations=config.agents.defaults.max_tool_iterations,
        context_window_tokens=config.agents.defaults.context_window_tokens,
        exec_config=config.tools.exec,
        cron_service=cron,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        session_manager=session_manager,
        interaction_config=config.interaction,
    )

    async def _print_gateway_message(channel: str, chat_id: str, content: str) -> None:
        if not content:
            return
        console.print()
        console.print(f"[cyan]{__logo__} {channel}:{chat_id}[/cyan]")
        console.print(Markdown(content))
        console.print()

    message_tool = agent.tools.get("message")
    if isinstance(message_tool, MessageTool):
        async def _send_from_gateway(msg) -> None:
            await _print_gateway_message(msg.channel, msg.chat_id, msg.content)

        message_tool.set_send_callback(_send_from_gateway)

    # Set cron callback (needs agent)
    async def on_cron_job(job: CronJob) -> str | None:
        """Execute a cron job through the agent."""
        from nanoclaw_mini.agent.tools.cron import CronTool
        from nanoclaw_mini.agent.tools.message import MessageTool
        from nanoclaw_mini.utils.evaluator import evaluate_response

        reminder_note = (
            "[Scheduled Task] Timer finished.\n\n"
            f"Task '{job.name}' has been triggered.\n"
            f"Scheduled instruction: {job.payload.message}"
        )

        cron_tool = agent.tools.get("cron")
        cron_token = None
        if isinstance(cron_tool, CronTool):
            cron_token = cron_tool.set_cron_context(True)
        try:
            response = await agent.process_direct(
                reminder_note,
                session_key=f"cron:{job.id}",
                channel=job.payload.channel or "cli",
                chat_id=job.payload.to or "direct",
            )
        finally:
            if isinstance(cron_tool, CronTool) and cron_token is not None:
                cron_tool.reset_cron_context(cron_token)

        message_tool = agent.tools.get("message")
        if isinstance(message_tool, MessageTool) and message_tool._sent_in_turn:
            return response

        if job.payload.deliver and job.payload.to and response:
            should_notify = await evaluate_response(
                response, job.payload.message, provider, agent.model,
            )
            if should_notify:
                await _print_gateway_message(job.payload.channel or "cli", job.payload.to, response)
        return response
    cron.on_job = on_cron_job

    def _pick_heartbeat_target() -> tuple[str, str]:
        """Pick the most recent non-system session for heartbeat-triggered tasks."""
        for item in session_manager.list_sessions():
            key = item.get("key") or ""
            if ":" not in key:
                continue
            channel, chat_id = key.split(":", 1)
            if channel != "system" and chat_id:
                return channel, chat_id
        return "cli", "direct"

    # Create heartbeat service
    async def on_heartbeat_execute(tasks: str) -> str:
        """Phase 2: execute heartbeat tasks through the full agent loop."""
        channel, chat_id = _pick_heartbeat_target()

        async def _silent(*_args, **_kwargs):
            pass

        return await agent.process_direct(
            tasks,
            session_key="heartbeat",
            channel=channel,
            chat_id=chat_id,
            on_progress=_silent,
        )

    async def on_heartbeat_notify(response: str) -> None:
        """Render heartbeat output in the local gateway process."""
        channel, chat_id = _pick_heartbeat_target()
        await _print_gateway_message(channel, chat_id, response)

    hb_cfg = config.gateway.heartbeat
    heartbeat = HeartbeatService(
        workspace=config.workspace_path,
        provider=provider,
        model=agent.model,
        on_execute=on_heartbeat_execute,
        on_notify=on_heartbeat_notify,
        interval_s=hb_cfg.interval_s,
        enabled=hb_cfg.enabled,
    )

    console.print("[dim]CLI-only build: no external chat channels are loaded in gateway mode.[/dim]")

    cron_status = cron.status()
    if cron_status["jobs"] > 0:
        console.print(f"[green]✓[/green] Cron: {cron_status['jobs']} scheduled jobs")

    console.print(f"[green]✓[/green] Heartbeat: every {hb_cfg.interval_s}s")

    async def run():
        try:
            await cron.start()
            await heartbeat.start()
            await agent.run()
        except KeyboardInterrupt:
            console.print("\nShutting down...")
        except Exception:
            import traceback
            console.print("\n[red]Error: Gateway crashed unexpectedly[/red]")
            console.print(traceback.format_exc())
        finally:
            await agent.close()
            heartbeat.stop()
            cron.stop()
            agent.stop()

    asyncio.run(run())




# ============================================================================
# Agent Commands
# ============================================================================


@app.command()
def agent(
    message: str = typer.Option(None, "--message", "-m", help="Message to send to the agent"),
    session_id: str = typer.Option("cli:direct", "--session", "-s", help="Session ID"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    markdown: bool = typer.Option(True, "--markdown/--no-markdown", help="Render assistant output as Markdown"),
    logs: bool = typer.Option(False, "--logs/--no-logs", help="Show nanoclaw-mini runtime logs during chat"),
):
    """Interact with the agent directly."""
    from loguru import logger

    from nanoclaw_mini.agent.loop import AgentLoop
    from nanoclaw_mini.bus.queue import MessageBus
    from nanoclaw_mini.config.paths import get_cron_dir
    from nanoclaw_mini.cron.service import CronService

    config = _load_runtime_config(config, workspace)
    _print_deprecated_memory_window_notice(config)
    sync_workspace_templates(config.workspace_path)

    bus = MessageBus()
    provider = _make_provider(config)

    # Create cron service for tool usage (no callback needed for CLI unless running)
    cron_store_path = get_cron_dir() / "jobs.json"
    cron = CronService(cron_store_path)

    if logs:
        logger.enable("nanoclaw_mini")
    else:
        logger.disable("nanoclaw_mini")

    agent_loop = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=config.agents.defaults.model,
        max_iterations=config.agents.defaults.max_tool_iterations,
        context_window_tokens=config.agents.defaults.context_window_tokens,
        exec_config=config.tools.exec,
        cron_service=cron,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        interaction_config=config.interaction,
    )

    # Show spinner when logs are off (no output to miss); skip when logs are on
    def _thinking_ctx():
        if logs:
            from contextlib import nullcontext
            return nullcontext()
        # Animated spinner is safe to use with prompt_toolkit input handling
        return console.status("[dim]nanoclaw-mini is thinking...[/dim]", spinner="dots")

    async def _cli_progress(content: str, *, tool_hint: bool = False) -> None:
        interaction = agent_loop.interaction_config
        if interaction and tool_hint and not interaction.send_tool_hints:
            return
        if interaction and not tool_hint and not interaction.send_progress:
            return
        console.print(f"  [dim]↳ {content}[/dim]")

    if message:
        # Single message mode — direct call, no bus needed
        async def run_once():
            with _thinking_ctx():
                response = await agent_loop.process_direct(message, session_id, on_progress=_cli_progress)
            _print_agent_response(response, render_markdown=markdown)
            await agent_loop.close()

        asyncio.run(run_once())
    else:
        # Interactive mode — route through bus like other channels
        from nanoclaw_mini.bus.events import InboundMessage
        _init_prompt_session()
        console.print(f"{__logo__} Interactive mode (type [bold]exit[/bold] or [bold]Ctrl+C[/bold] to quit)\n")

        if ":" in session_id:
            cli_channel, cli_chat_id = session_id.split(":", 1)
        else:
            cli_channel, cli_chat_id = "cli", session_id

        def _handle_signal(signum, frame):
            sig_name = signal.Signals(signum).name
            _restore_terminal()
            console.print(f"\nReceived {sig_name}, goodbye!")
            sys.exit(0)

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)
        # SIGHUP is not available on Windows
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, _handle_signal)
        # Ignore SIGPIPE to prevent silent process termination when writing to closed pipes
        # SIGPIPE is not available on Windows
        if hasattr(signal, 'SIGPIPE'):
            signal.signal(signal.SIGPIPE, signal.SIG_IGN)

        async def run_interactive():
            bus_task = asyncio.create_task(agent_loop.run())
            turn_done = asyncio.Event()
            turn_done.set()
            turn_response: list[str] = []

            async def _consume_outbound():
                while True:
                    try:
                        msg = await asyncio.wait_for(bus.consume_outbound(), timeout=1.0)
                        if msg.metadata.get("_progress"):
                            is_tool_hint = msg.metadata.get("_tool_hint", False)
                            interaction = agent_loop.interaction_config
                            if interaction and is_tool_hint and not interaction.send_tool_hints:
                                pass
                            elif interaction and not is_tool_hint and not interaction.send_progress:
                                pass
                            else:
                                await _print_interactive_line(msg.content)

                        elif not turn_done.is_set():
                            if msg.content:
                                turn_response.append(msg.content)
                            turn_done.set()
                        elif msg.content:
                            await _print_interactive_response(msg.content, render_markdown=markdown)

                    except asyncio.TimeoutError:
                        continue
                    except asyncio.CancelledError:
                        break

            outbound_task = asyncio.create_task(_consume_outbound())

            try:
                while True:
                    try:
                        _flush_pending_tty_input()
                        user_input = await _read_interactive_input_async()
                        command = user_input.strip()
                        if not command:
                            continue

                        if _is_exit_command(command):
                            _restore_terminal()
                            console.print("\nGoodbye!")
                            break

                        turn_done.clear()
                        turn_response.clear()

                        await bus.publish_inbound(InboundMessage(
                            channel=cli_channel,
                            sender_id="user",
                            chat_id=cli_chat_id,
                            content=user_input,
                        ))

                        with _thinking_ctx():
                            await turn_done.wait()

                        if turn_response:
                            _print_agent_response(turn_response[0], render_markdown=markdown)
                    except KeyboardInterrupt:
                        _restore_terminal()
                        console.print("\nGoodbye!")
                        break
                    except EOFError:
                        _restore_terminal()
                        console.print("\nGoodbye!")
                        break
            finally:
                agent_loop.stop()
                outbound_task.cancel()
                await asyncio.gather(bus_task, outbound_task, return_exceptions=True)
                await agent_loop.close()

        asyncio.run(run_interactive())


# ============================================================================
# Channel Commands
# ============================================================================


def _get_bridge_dir() -> Path:
    """Unused bridge helper placeholder."""
    raise typer.Exit(1)
    if False:

        console.print("[green]✓[/green] Bridge ready\n")


# ============================================================================
# Model Commands
# ============================================================================

models_app = typer.Typer(help="List and switch Codex models")
app.add_typer(models_app, name="models")


def _fetch_codex_models(config: Config):
    provider = _make_provider(config)
    try:
        return asyncio.run(provider.list_models())
    except RuntimeError as exc:
        message = str(exc)
        if "OAuth credentials not found" in message:
            console.print("[red]Not logged in.[/red] Run [cyan]nanoclaw-mini provider login codex[/cyan] first.")
            raise typer.Exit(1)
        console.print(f"[red]Failed to fetch Codex models:[/red] {message}")
        raise typer.Exit(1)


@models_app.command("list")
def models_list(
    config: str | None = typer.Option(None, "--config", "-c", help="Path to config file"),
    json_output: bool = typer.Option(False, "--json", help="Print raw model data as JSON"),
):
    """Fetch the available Codex models for the current login."""
    loaded, _ = _load_editable_config(config)
    current_model = loaded.agents.defaults.model
    models = _fetch_codex_models(loaded)

    if json_output:
        payload = [
            {
                "id": model.id,
                "slug": model.slug,
                "displayName": model.display_name,
                "description": model.description,
                "contextWindow": model.context_window,
                "defaultReasoningLevel": model.default_reasoning_level,
                "supportedReasoningLevels": list(model.supported_reasoning_levels),
                "visibility": model.visibility,
                "supportedInApi": model.supported_in_api,
                "priority": model.priority,
                "isCurrent": _current_model_matches(current_model, model.id, model.slug),
            }
            for model in models
        ]
        console.print_json(json=json.dumps(payload, ensure_ascii=False))
        return

    table = Table(title="Available Codex Models")
    table.add_column("Current", style="cyan", no_wrap=True)
    table.add_column("Model", style="bold")
    table.add_column("Reasoning", style="magenta")
    table.add_column("Context", justify="right")
    table.add_column("Description", overflow="fold")

    for model in models:
        current_marker = "*" if _current_model_matches(current_model, model.id, model.slug) else ""
        reasoning = model.default_reasoning_level or "-"
        if model.supported_reasoning_levels:
            reasoning = f"{reasoning} ({', '.join(model.supported_reasoning_levels)})"
        description = model.description or "-"
        table.add_row(
            current_marker,
            model.id,
            reasoning,
            _short_context_window(model.context_window),
            description,
        )

    console.print(table)
    console.print(f"[dim]Current model: {current_model}[/dim]")


@models_app.command("set")
def models_set(
    model: str = typer.Argument(..., help="Model slug or full model id"),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to config file"),
    force: bool = typer.Option(False, "--force", help="Set the model even if remote validation fails"),
):
    """Set the default model in config.json."""
    from nanoclaw_mini.config.loader import save_config

    loaded, config_path = _load_editable_config(config)
    selected = _normalize_codex_model(model)
    available_models = None

    if not force:
        try:
            available_models = _fetch_codex_models(loaded)
        except typer.Exit:
            console.print("[yellow]Skipping remote validation. Use --force to silence this warning.[/yellow]")

    if available_models is not None:
        available_ids = {item.id for item in available_models}
        available_slugs = {item.slug for item in available_models}
        if selected not in available_ids and selected.split("/", 1)[1] not in available_slugs:
            console.print(f"[red]Model not found in the current Codex account:[/red] {selected}")
            console.print("Run [cyan]nanoclaw-mini models list[/cyan] to inspect the available models, or pass [cyan]--force[/cyan].")
            raise typer.Exit(1)

    previous = loaded.agents.defaults.model
    loaded.agents.defaults.model = selected
    save_config(loaded, config_path)

    console.print("[green]Updated default model[/green]")
    console.print(f"  From: [dim]{previous}[/dim]")
    console.print(f"  To:   [cyan]{selected}[/cyan]")
    console.print(f"  Config: [dim]{config_path}[/dim]")


@models_app.command("choose")
def models_choose(
    config: str | None = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Interactively choose a model from the current Codex account."""
    from nanoclaw_mini.config.loader import save_config

    loaded, config_path = _load_editable_config(config)
    current_model = loaded.agents.defaults.model
    models = _fetch_codex_models(loaded)

    console.print(f"{__logo__} Choose a Codex model\n")
    for index, model in enumerate(models, start=1):
        current_marker = " [current]" if _current_model_matches(current_model, model.id, model.slug) else ""
        reasoning = model.default_reasoning_level or "-"
        console.print(f"{index}. [cyan]{model.id}[/cyan]{current_marker}")
        console.print(f"   reasoning: {reasoning}")
        if model.description:
            console.print(f"   {model.description}")

    choice = typer.prompt("Select a model number", type=int)
    if choice < 1 or choice > len(models):
        console.print(f"[red]Invalid selection:[/red] {choice}")
        raise typer.Exit(1)

    selected = models[choice - 1].id
    loaded.agents.defaults.model = selected
    save_config(loaded, config_path)

    console.print(f"[green]Selected model:[/green] [cyan]{selected}[/cyan]")
    console.print(f"[dim]Saved to {config_path}[/dim]")


# ============================================================================
# Status Commands
# ============================================================================


def _get_openai_codex_account_id() -> str | None:
    """Return the active Codex OAuth account ID when available."""
    try:
        from oauth_cli_kit import get_token
    except ImportError:
        return None

    try:
        token = get_token()
    except Exception:
        return None

    if not (token and getattr(token, "access", None)):
        return None

    return getattr(token, "account_id", None) or "authenticated"


@app.command()
def status():
    """Show nanoclaw-mini status."""
    from nanoclaw_mini.config.loader import get_config_path, load_config

    config = load_config()
    config_path = get_config_path()
    workspace = config.workspace_path

    console.print(f"{__logo__} nanoclaw-mini Status\n")

    console.print(f"Config: {config_path} {'[green]✓[/green]' if config_path.exists() else '[red]✗[/red]'}")
    console.print(f"Workspace: {workspace} {'[green]✓[/green]' if workspace.exists() else '[red]✗[/red]'}")

    console.print(f"Model: {config.agents.defaults.model}")
    account_id = _get_openai_codex_account_id()
    if account_id:
        console.print(f"OpenAI Codex: [green]OAuth ready[/green] [dim]{account_id}[/dim]")
    else:
        console.print("OpenAI Codex: [dim]not logged in[/dim]")
        if False:
            if spec.is_oauth:
                console.print(f"{spec.label}: [green]✓ (OAuth)[/green]")
            elif spec.is_local:
                # Local deployments show api_base instead of api_key
                if p.api_base:
                    console.print(f"{spec.label}: [green]✓ {p.api_base}[/green]")
                else:
                    console.print(f"{spec.label}: [dim]not set[/dim]")
            else:
                has_key = bool(p.api_key)
                console.print(f"{spec.label}: {'[green]✓[/green]' if has_key else '[dim]not set[/dim]'}")


# ============================================================================
# OAuth Login
# ============================================================================

provider_app = typer.Typer(help="Manage providers")
app.add_typer(provider_app, name="provider")


_LOGIN_HANDLERS: dict[str, callable] = {}


def _register_login(name: str):
    def decorator(fn):
        _LOGIN_HANDLERS[name] = fn
        return fn
    return decorator


@provider_app.command("login")
def provider_login(
    provider: str = typer.Argument(..., help="Codex login target ('codex' or 'openai-codex')"),
):
    """Authenticate with OpenAI Codex OAuth."""
    from nanoclaw_mini.providers.registry import PROVIDERS

    aliases = {"codex": "openai_codex"}
    normalized = provider.strip().lower()
    key = aliases.get(normalized, normalized).replace("-", "_")
    spec = next((s for s in PROVIDERS if s.name == key and s.is_oauth), None)
    if not spec:
        names = "codex, " + ", ".join(s.name.replace("_", "-") for s in PROVIDERS if s.is_oauth)
        console.print(f"[red]Unknown OAuth provider: {provider}[/red]  Supported: {names}")
        raise typer.Exit(1)

    handler = _LOGIN_HANDLERS.get(spec.name)
    if not handler:
        console.print(f"[red]Login not implemented for {spec.label}[/red]")
        raise typer.Exit(1)

    console.print(f"{__logo__} OAuth Login - {spec.label}\n")
    handler()


@_register_login("openai_codex")
def _login_openai_codex() -> None:
    try:
        from oauth_cli_kit import get_token, login_oauth_interactive
        token = None
        try:
            token = get_token()
        except Exception:
            pass
        if not (token and token.access):
            console.print("[cyan]Starting interactive OAuth login...[/cyan]\n")
            token = login_oauth_interactive(
                print_fn=lambda s: console.print(s),
                prompt_fn=lambda s: typer.prompt(s),
            )
        if not (token and token.access):
            console.print("[red]✗ Authentication failed[/red]")
            raise typer.Exit(1)
        console.print(f"[green]✓ Authenticated with OpenAI Codex[/green]  [dim]{token.account_id}[/dim]")
    except ImportError:
        console.print("[red]oauth_cli_kit not installed. Run: pip install oauth-cli-kit[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
