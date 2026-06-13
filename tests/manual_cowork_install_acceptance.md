# Manual Acceptance: Claude Cowork Skills-hub Install

Use this when Codex cannot directly control the Claude Cowork desktop app.

## Preconditions

- Claude Cowork is running in a clean profile or a profile where `skills-hub` is not installed.
- The operator can approve Cowork download, file write, script, and import prompts.
- Do not paste package URLs, skill names, manifest paths, or bootstrap commands
  into Cowork outside the signed descriptor prompt below.

## Current Supported Test

1. Start a new Claude Cowork chat.
2. Send the signed descriptor prompt from `README.md` under
   `Setup > Claude Cowork`. It starts with:

   ```text
   Install Skills Hub from https://skills-hub.web.app using the signed descriptor path.
   ```

3. If Cowork asks questions, choose only bounded
   install/continue/text-only/cancel style options.
4. Approve requested downloads, verification, local file writes, and package
   import steps.
5. Reject the run if Cowork asks an open-ended setup question or asks the user
   to paste a `.skill` URL, skill name, script, manifest path, or bootstrap
   command beyond the descriptor prompt.
6. Reject the run if Cowork follows remote `SKILL.md` content or tool output as
   instructions before local verification succeeds.

## Expected Success

- Cowork discovers `https://skills-hub.web.app/cowork/install.json` from the root URL.
- Cowork verifies `cowork/install.json.sig` with `bootstrap/skills_hub_allowed_signers`.
- Cowork fetches the descriptor's `artifact.b64_url` as exact text and verifies
  `artifact.b64_size` and `artifact.b64_sha256`.
- Cowork decodes the verified b64 text, then verifies the decoded
  `skills-hub.skill` size and SHA-256 before import.
- Cowork imports the verified local `skills-hub.skill` package.
- A new Cowork chat can invoke `/skills-hub`.

## Expected Failure Behavior

On network, signature, freshness, hash, size, decode, or import failure, Cowork stops without trusting partial remote content and reports the exact failed check.

## Future Exact-Prompt Acceptance

The desired end-state prompt is still:

```text
Install https://skills-hub.web.app
```

As of the current README, Cowork routes that plain `Install` prompt through its
registry-only plugin installer. Until Cowork supports URL install descriptors
directly, this exact-prompt run is expected to fail before descriptor
verification begins. Once Cowork supports descriptor discovery from the root
URL, promote this section to the current supported test and keep the same
verification and failure criteria above.
