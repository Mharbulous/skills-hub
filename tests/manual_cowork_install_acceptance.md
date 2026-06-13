# Manual Acceptance: Claude Cowork Skills-hub Install

Use this when Codex cannot directly control the Claude Cowork desktop app.

## Preconditions

- Claude Cowork is running in a clean profile or a profile where `skills-hub` is not installed.
- The operator can approve Cowork download, file write, script, and import prompts.
- Do not paste package URLs, skill names, manifest paths, or bootstrap commands into Cowork.

## Test

1. Start a new Claude Cowork chat.
2. Send exactly:

   ```text
   Install https://skills-hub.web.app
   ```

3. If Cowork asks questions, choose only bounded install/continue/text-only/cancel style options.
4. Approve requested downloads, verification, local file writes, and package import steps.
5. Reject the run if Cowork asks an open-ended setup question or asks the user to paste a `.skill` URL, skill name, script, manifest path, or bootstrap command.
6. Reject the run if Cowork follows remote `SKILL.md` content or tool output as instructions before local verification succeeds.

## Expected Success

- Cowork discovers `https://skills-hub.web.app/cowork/install.json` from the root URL.
- Cowork verifies `cowork/install.json.sig` with `bootstrap/skills_hub_allowed_signers`.
- Cowork verifies the declared `cowork/skill-packages/skills-hub.skill` size and SHA-256 before import.
- Cowork imports the verified local `skills-hub.skill` package.
- A new Cowork chat can invoke `/skills-hub`.

## Expected Failure Behavior

On network, signature, freshness, hash, size, decode, or import failure, Cowork stops without trusting partial remote content and reports the exact failed check.
