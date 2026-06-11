# C# / WPF Reference

Language-specific patterns for the fallback-remover skill.

## File Types

`.cs` only. Exclude `obj/`, `bin/`, test projects (files under `*Tests/`, `*Test/`, or containing `[Fact]`/`[Test]`/`[TestMethod]`).

## Source Directories

Scan all `.cs` files in project. Infer source from `.csproj` location.

## Severity Tiers

Classify each finding under its **highest** matching tier only (no duplicates).

### CRITICAL — Catch + return null/default/fallback

Catch blocks that return `null`, `default`, `new List<T>()`, `Array.Empty<T>()`, `false`, `0`, `string.Empty`, or any constructed default. The caller cannot distinguish success from masked failure.

```csharp
// Silent fallback
catch (Exception ex)
{
    Debug.WriteLine($"Failed: {ex.Message}");
    return null;
}
```

### HIGH — Catch with only Debug/Console logging, no rethrow

Catch blocks that only call `Debug.WriteLine` or `Console.WriteLine` without rethrowing or setting error state. Also: catch blocks whose comment says "log" but contain no actual log statement.

```csharp
// Silent — logs but doesn't surface
catch (Exception ex)
{
    Debug.WriteLine($"Failed: {ex.Message}");
}

// Worse — comment lies about logging
catch
{
    // Log and continue - calendar context is optional
    // ^^^ no actual log statement!
}
```

### MEDIUM — Empty catch blocks without documenting comment

Bare `catch { }` or `catch (Exception) { }` without a comment explaining why the error is safe to ignore.

## False Positive Rules

**EXCLUDE these patterns:**

1. **Dispose/cleanup** — `catch { }` in `Dispose()`, `Dispose(bool)`, finalizers, or shutdown methods. COM cleanup (`Marshal.ReleaseComObject`) in dispose is always safe to swallow.

2. **Test cleanup** — `catch { }` in test `Dispose` or `[TearDown]` methods. Test teardown is inherently best-effort.

3. **Windows hook callbacks** — `catch { }` in `HookCallback`, `WndProc`, or any method called from a Windows message pump. Exceptions in hook callbacks crash the process — suppression is required by the Windows API contract.

4. **`async void` event handlers** — catch-all in `async void` methods that are WPF event handlers (subscribed via `+=`). Unhandled exceptions in `async void` crash the process. The catch is mandatory; the question is whether it surfaces the error to the user (dialog, status bar, etc.).

5. **Logging infrastructure** — `catch { }` inside logging/diagnostic methods (`DiagLog`, `WriteLog`, `CaptureLog.Write`). Loggers must not throw.

6. **Catch-rethrow after rollback** — `catch { transaction.Rollback(); throw; }` is NOT a silent fallback — it rethrows.

7. **Documented best-effort with comment** — catch blocks where an adjacent comment explicitly explains why failure is non-critical AND the service is genuinely optional (e.g., cloud upload when local capture succeeds independently).

8. **Specific exception type guards** — `catch (UnauthorizedAccessException)` or `catch (COMException)` in COM interop / P/Invoke where the specific failure mode is expected and the method contract handles it (e.g., returning `false` from a validation method for invalid input).

**When in doubt, INCLUDE the finding.**

### Borderline Patterns — Flag but note context

These are not automatic false positives. Present them to the user with context:

- **COM interop `catch { return null; }`** — Expected when Office isn't installed, but bare `catch` also swallows programming errors. Flag as CRITICAL but note COM context.
- **Device monitoring silent catches** — Best-effort device queries (audio/video) with no logging. Flag as HIGH — at minimum needs `Debug.WriteLine`.
- **Nested silent catches** — When both a method AND its caller swallow exceptions (double-wrapping). Flag the outer catch — inner catch should be the documented boundary.

## Fix Patterns

**CRITICAL — catch + return null/default:**
```csharp
// BEFORE
catch (Exception ex)
{
    Debug.WriteLine($"Failed: {ex.Message}");
    return null;
}

// AFTER — propagate
catch (Exception ex)
{
    Debug.WriteLine($"Failed: {ex.Message}");
    throw;
}
// or if best-effort with documented reason:
catch (Exception ex)
{
    Debug.WriteLine($"Failed: {ex.Message}");
    return null; // Best-effort: [reason failure is non-critical]
}
```

**HIGH — log-only catch:**
```csharp
// BEFORE
catch (Exception ex)
{
    Debug.WriteLine($"Failed: {ex.Message}");
}

// AFTER — if failure matters:
catch (Exception ex)
{
    Debug.WriteLine($"Failed: {ex.Message}");
    throw;
}
// AFTER — if truly best-effort, document:
catch (Exception ex)
{
    Debug.WriteLine($"Failed: {ex.Message}");
    // Best-effort: [reason]
}
```

**HIGH — lying comment (says "log" but doesn't):**
```csharp
// BEFORE
catch
{
    // Log and continue - context is optional
}

// AFTER — either add the log or fix the comment:
catch (Exception ex)
{
    Debug.WriteLine($"[Component] Context fetch failed: {ex.Message}");
    // Best-effort: context is optional enhancement
}
```

**MEDIUM — empty catch:**
```csharp
// BEFORE
catch { }

// AFTER
catch { /* Best-effort: [reason] */ }
```

## Test Runner Detection

Check `.csproj` for: `xunit`, `nunit`, `MSTest.TestFramework`. Run `dotnet test` after fixing to verify no regressions.
