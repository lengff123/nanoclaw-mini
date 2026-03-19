# nanoclaw-mini Desktop

This is a Rust desktop manager for `nanoclaw-mini`.

It is designed to manage the repository at:

- `https://github.com/lengff123/nanoclaw-mini`

## Current features

- Check whether `nanoclaw-mini` is already present on disk
- Clone and install it with `git clone` + `python -m pip install -e .`
- Open a one-click terminal for `nanoclaw-mini onboard`
- Open a one-click terminal for `nanoclaw-mini provider login codex`
- Open a one-click terminal for `nanoclaw-mini agent`
- Check the local commit against the remote repository
- Update the local clone with `git pull --ff-only`
- Uninstall the managed clone and remove the editable Python package
- Enable or disable desktop app autostart on Windows and macOS

## Build

```powershell
cd C:\Users\LAB\Downloads\new\nanoclaw-mini\nanoclaw-mini-desktop
cargo run
```

## Notes

- The current repository URL is hard-coded to the user's GitHub repository.
- Autostart uses the Windows `Run` registry key on Windows and `LaunchAgents` on macOS.
- The app expects `git` and Python to be available in `PATH`.
- `Initialize`, `Codex Login`, and `Launch Agent` open a separate terminal window.
- Quick launch actions currently support Windows and macOS.
