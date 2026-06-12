# Desktop App Platform — Promote Subfile

Platform-specific procedures for promoting .NET desktop applications (WPF/WinForms). Loaded by the main `/promote` orchestrator — do not invoke directly.

## PREFLIGHT

### Locate the Solution

Find the solution file:
```bash
find . -maxdepth 2 -name "*.sln" | head -1
```

If found in a subdirectory (e.g., `dotnet/`), note the solution root for subsequent commands.

### Run Tests
```bash
dotnet test [SOLUTION_PATH]
```

**If tests fail:** STOP and report failures. Do NOT proceed. (No auto-repair subagent for dotnet — test failures must be fixed manually.)

### Run Build (validation only)
```bash
dotnet build [SOLUTION_PATH]
```

**If build fails:** STOP. Do NOT proceed.

## VERSION_SOURCE

When the main orchestrator finds no semver git tags (step 2.1), check for a VERSION file:

```bash
cat scripts/VERSION 2>/dev/null | tr -d '\r\n'
```

If found, the value (e.g., `0.2.18`) represents the next unreleased version. Use it as-is for this promotion — do NOT bump it further.

Format the tag as `v{VERSION}` (e.g., `v0.2.18`).

If `scripts/VERSION` does not exist either, this is the first promotion — use `v1.0.0`.

**Transition note:** Once the first promote-created semver tag exists, subsequent promotions will find it via `git tag` in step 2.1 and apply normal bump logic. The VERSION file fallback is only needed for the initial migration from `build.sh`.

## VERSION_WRITE

After the version has been determined (step 2.3), and BEFORE creating the PR (step 3.1), update the VERSION file on main so the version bump is included in the promotion:

```bash
# Determine the NEXT version (one patch above the version being promoted)
# e.g., if promoting v0.2.18, write 0.2.19 so the next promote has a correct fallback
IFS='.' read -r MAJOR MINOR PATCH <<< "[VERSION_WITHOUT_V_PREFIX]"
NEXT_PATCH=$((PATCH + 1))
echo "$MAJOR.$MINOR.$NEXT_PATCH" > scripts/VERSION
git add scripts/VERSION
git commit -m "chore: bump VERSION to $MAJOR.$MINOR.$NEXT_PATCH after v[VERSION] release"
git push origin main
```

If `scripts/VERSION` does not exist, skip this step.

## BUILD_AND_DEPLOY

**Critical:** Must be on the `production` branch.

### Discover Project Paths

Find the main executable project:
```bash
find . -name "*.csproj" -exec grep -l "<OutputType>WinExe</OutputType>" {} \;
```

Extract the assembly name:
```bash
grep -oP '<AssemblyName>\K[^<]+' [CSPROJ_PATH]
```

Set variables:
- `PROJECT_PATH` — the `.csproj` path found above
- `APP_NAME` — the extracted assembly name (e.g., `SyncoPaid`)
- `VERSION` — the version being promoted, without the `v` prefix (e.g., `0.2.18`)
- `VERSION_DASHED` — version with dots replaced by dashes (e.g., `0-2-18`)
- `OUTPUT_DIR` — `app/releases` (create if missing: `mkdir -p app/releases`)

### Build Single-File Executable

```bash
dotnet publish "$PROJECT_PATH" \
    -c Release \
    -r win-x64 \
    -o "$OUTPUT_DIR" \
    -p:PublishSingleFile=true \
    -p:IncludeNativeLibrariesForSelfExtract=true \
    -p:Version="$VERSION" \
    -p:FileVersion="$VERSION" \
    -p:InformationalVersion="$VERSION" \
    --self-contained true
```

Shaders and other MSBuild targets (e.g., `CompileShaders`) run automatically during publish — no manual step needed.

### Rename and Clean

```bash
mv "$OUTPUT_DIR/${APP_NAME}.exe" "$OUTPUT_DIR/${APP_NAME}-v${VERSION_DASHED}.exe"
rm -f "$OUTPUT_DIR"/*.pdb
```

### Verify Output

```bash
ls -lh "$OUTPUT_DIR/${APP_NAME}-v${VERSION_DASHED}.exe"
```

There is **no deployment step** for desktop apps. The executable in `app/releases/` is the deliverable.

## SUMMARY_EXTRAS

```
Executable: [OUTPUT_DIR]/[APP_NAME]-v[VERSION_DASHED].exe ([FILE_SIZE])
```

## ERROR_RECOVERY

- **Test failures**: Report and stop — no auto-repair for dotnet tests
- **Build/publish failures**: Check for missing SDK (`dotnet --list-sdks`), missing dependencies, or shader compiler issues; report error
- **Shader compilation**: If `fxc.exe` is not found, the MSBuild target is set to `ContinueOnError="true"` — the build may succeed if a pre-compiled `.ps` file exists from a previous compilation. Check and warn if the `.ps` file is stale.
