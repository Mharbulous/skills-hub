---
description: Capture screenshots of visible Windows desktop application windows as PNG files for visual verification. Use when Codex needs to inspect, troubleshoot, or verify a non-browser desktop app, WPF UI, error dialog, installer, local app preview, desktop app screenshot, or any visible Windows window that Playwright/browser tools cannot capture. Use this skill for requests like "verify the UI visually", "capture screenshots", "the desktop app launches but I don't see a window", and WPF visual checks.
---

## Codex Usage

Materialize this skill folder from the full install or Skills-hub per-skill
tarball, set `SKILL_DIR` to that extracted folder, and use the bundled CLI
(PowerShell):

```powershell
python "$env:SKILL_DIR\src\glimpse.py" capture "window title"
```

Desktop window access usually requires running the command outside the sandbox. When `windows` returns no windows, or capture cannot see a visible desktop app, rerun the command with escalated shell permissions.

## Windows desktop verification workflow

When visual verification depends on a newly changed desktop binary, keep build, launch, and capture in the same host-visible context. A common failure mode in this environment is building inside the sandbox, then launching a host desktop process that still sees the old binary.

1. Close stale target processes before rebuilding, especially WPF apps. Hidden or failed processes can keep old `.exe` and `.dll` files locked.
2. Build the desktop app in the same context that will launch it. If the app must run on the user's desktop, build with escalated/host-visible shell permissions when needed.
3. Launch the app with an explicit working directory and desktop access.
4. Run `glimpse.py windows`. If it returns no windows from the sandbox, rerun it with escalated shell permissions before concluding the app has no window.
5. Navigate to the exact state the user reported. For simple clicks, Windows UI Automation is often more reliable than trying to drive the app through screenshots.
6. Capture the target window and inspect the PNG with the image viewer. A saved screenshot path is not verification by itself.
7. Close the launched app after verification so it does not lock build outputs for later tests or rebuilds.

Useful PowerShell patterns:

```powershell
Get-Process SyncoPaid.View -ErrorAction SilentlyContinue |
    Select-Object ProcessName,Id,MainWindowTitle
```

```powershell
Start-Process -FilePath .\bin\Debug\net8.0-windows\MyApp.exe `
    -WorkingDirectory .\bin\Debug\net8.0-windows
```

```powershell
Stop-Process -Id 12345
```

## WPF and local app troubleshooting

If a process exists but no visible window appears, do not keep relaunching blindly. Check the visible-window list, process `MainWindowTitle`, app crash logs, and Windows Event Viewer around the launch time.

For WPF, `System.Windows.Window` `TypeInitializationException` usually hides the real cause in an inner exception. If the app log only records the outer exception and stack trace, prefer improving the app's crash logging to write `Exception.ToString()`, which includes nested exceptions.

Also check launch environment values before assuming the UI code is broken:

```powershell
foreach ($name in 'windir','SystemRoot','USERPROFILE','LOCALAPPDATA','TEMP') {
    [PSCustomObject]@{ Name = $name; Value = [Environment]::GetEnvironmentVariable($name) }
}
```

WPF can fail during `Window` initialization when expected Windows environment variables such as `windir` are missing, even if `SystemRoot` is present.

Windows UI Automation can move the app into the state that needs verification:

```powershell
Add-Type -AssemblyName UIAutomationClient
$root = [System.Windows.Automation.AutomationElement]::RootElement
$window = $root.FindFirst(
    [System.Windows.Automation.TreeScope]::Children,
    (New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        'SyncoPaid - Pending Review')))
$button = $window.FindFirst(
    [System.Windows.Automation.TreeScope]::Descendants,
    (New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        'View Raw Captures')))
$button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
```

## Anti-patterns

- Building in the sandbox, then launching a host desktop app and assuming it uses the rebuilt binary.
- Repeatedly launching the app without killing hidden stale instances first.
- Treating desktop app verification like browser automation.
- Accepting an empty sandboxed `windows` result without retrying with desktop access.
- Capturing only the initial screen instead of navigating to the failure state the user reported.
- Reporting a screenshot path without opening and inspecting the image.
- Ignoring crash logs because the app process exists.

## Lightweight manual eval prompts

Use these prompts to sanity-check future updates to this skill:

- "Verify the WPF app visually after my code change and capture screenshots."
- "The desktop app launches but I don't see a window; use Glimpse to figure out what's happening."
- "Open the Raw Captures screen, capture it, and confirm the rows/details are visible."

Expected behavior: mention host-visible build/run consistency, check for stale processes, use escalated `glimpse.py windows` when needed, capture and inspect screenshots, and close the app afterward.
