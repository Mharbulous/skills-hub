# Manual Acceptance: Claude Cowork Skills-hub Install

Use this when Codex cannot directly control the Claude Cowork desktop app.

## Preconditions

- Claude Cowork is running in a clean profile or a profile where `skills-hub` is not installed.
- The operator can approve bounded Cowork install prompts.
- If this Cowork build cannot discover marketplaces from a bare root URL, the
  Skills-hub marketplace has been added or published through Cowork's
  plugin/marketplace mechanism before testing the exact prompt.

## Current Supported Test

1. Start a new Claude Cowork chat.
2. Send:

   ```text
   Install https://skills-hub.web.app
   ```

3. If Cowork shows a `skills-hub` plugin card, install it.
4. Reject the run if Cowork enters a base64 decode loop, asks for open-ended
   setup input, or asks the user to paste a `.skill` URL, skill name, script,
   manifest path, or bootstrap command.

## Expected Success

- Cowork discovers the Skills-hub marketplace or registered plugin from the root URL.
- Cowork presents the `skills-hub` plugin card without using web_fetch/base64.
- Installing the plugin makes `/skills-hub` available in a new chat.
- `/skills-hub` bare command shows local help/status without fetching remote content.
- `/skills-hub inventory`, `/skills-hub install <skill>`, and `/skills-hub update`
  still verify signed Skills-hub artifacts and fail closed on verification errors.

## Descriptor Fallback Test

Use this only when testing the fallback path from `README.md` under
`Setup > Claude Cowork > Descriptor Fallback`.

- Cowork discovers `https://skills-hub.web.app/cowork/install.json` from the root URL.
- Cowork verifies `cowork/install.json.sig` with `bootstrap/skills_hub_allowed_signers`.
- Cowork fetches the descriptor's `artifact.b64_url` as exact text only if it
  has a byte-preserving fetch-to-file path.
- Cowork verifies `artifact.b64_size`, `artifact.b64_sha256`, and the decoded
  `skills-hub.skill` size and SHA-256 before import.
- A new Cowork chat can invoke `/skills-hub`.

## Expected Failure Behavior

On network, signature, freshness, hash, size, decode, import, or presentation
failure, Cowork stops without trusting partial remote content and reports the
exact failed check. If no byte-preserving fetch-to-file path exists during
descriptor fallback, Cowork stops with
`BLOCKED: no byte-preserving fetch-to-file path`.

## External Discovery Gate

If Cowork cannot discover the marketplace from the bare root URL, exact-prompt
acceptance is blocked until the marketplace is added or published through
Cowork's external plugin registry.
