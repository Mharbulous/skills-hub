# Manual Acceptance: Claude Cowork Skills-hub Install

Use this when Codex cannot directly control the Claude Cowork desktop app.

## Preconditions

- Claude Cowork is running in a clean profile or a profile where `skills-hub` is not installed.
- The operator can approve bounded Cowork install prompts.
- The Skills-hub GitHub repository is public, or Cowork has authenticated Git
  access to clone it.

## Current Supported Test

1. Open **Customize > Plugins > Add marketplace**.
2. Choose **Add from a repository**.
3. Enter:

   ```text
   https://github.com/Mharbulous/skills-hub.git
   ```

4. If Cowork shows a `skills-hub` plugin card, install it.
5. Start a new Cowork chat and send:

   ```text
   /skills-hub
   ```

6. Reject the run if Cowork enters a base64 decode loop, asks for open-ended
   setup input, or asks the user to paste a `.skill` URL, skill name, script,
   manifest path, or bootstrap command.

## Expected Success

- Cowork discovers the root `.claude-plugin/marketplace.json` from the Git repository.
- Cowork presents the `skills-hub` plugin card without using web_fetch/base64.
- Installing the plugin makes `/skills-hub` available in a new chat.
- `/skills-hub` bare command shows local help/status without fetching remote content.
- `/skills-hub inventory`, `/skills-hub install <skill>`, and `/skills-hub update`
  use the public GitHub repo archive and do not require Firebase/static hosted
  package artifacts.

## GitHub Package Test

Use this after the plugin is installed.

1. Start a new Claude Cowork chat.
2. Send:

   ```text
   /skills-hub install assemble-affidavit
   ```

3. Cowork should download the public GitHub repo archive, build
   `assemble-affidavit.skill` locally, and present one Save-skill card.

## Expected Failure Behavior

On network, zip decode, package build, import, or presentation failure, Cowork
stops without presenting a partial package and reports the exact failed check.

## External Discovery Gate

If Cowork cannot install the repository marketplace directly, acceptance is
blocked until Cowork supports public Git repository marketplaces or the plugin
is published through Cowork's external plugin registry.
