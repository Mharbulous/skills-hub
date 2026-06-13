# Database Initialization Protocol

Run this protocol when `coclerk.json` does not exist at `AppData\Roaming\Coclerk\coclerk.json` relative to the current user's home directory.

## Step 1 — Inform and ask for database name

Use AskUserQuestion:

> "It looks like you haven't set up a Coclerk database yet. Let's get that done. What would you like your database to be named?"

Options:
1. **practice.db** — "Default name, recommended for most users"
2. **Something else** — "You'll be prompted to type a custom name"
3. **I already have a database** — "Help me locate an existing database file"

If the user picks option 3, ask them to point you to the `.db` file. Once located, use that path and filename for the config and skip to Step 3.

## Step 2 — Ask the user to select a folder

Tell the user:

> "I need to create a database file to store your practice data locally — things like matter information and retainer balances. This file stays on your computer and is never sent anywhere. I'll need you to choose a folder where I can save it, and grant me access to that folder so I can create and update the database there."

Use `request_cowork_directory` to let the user select a local folder. This grants you read/write access to that folder.

If the user doesn't grant access, stop and explain that you need folder access to create the database.

## Step 3 — Ask for accounting system

Use AskUserQuestion:

> "What accounting system do you use for your practice?"

Options:
1. **UNITY** — "UNITY Accounting / UNITY4"
2. **QuickBooks** — "QuickBooks Online or Desktop"
3. **Clio** — "Clio Manage"
4. **Other** — "You'll be prompted to type the name"

## Step 4 — Privacy and Data Storage Briefing

Before creating the database, brief the user on how their data will be handled. Cover all three points conversationally — do not dump a wall of text:

1. **Local storage.** The database will remain on their local computer. Claude will only query it in response to their requests during active sessions. No client data is uploaded to Anthropic's servers as part of the database workflow.

2. **Training opt-out.** Recommend visiting Claude's privacy settings and disabling the option that allows Anthropic to use conversations to train models. This adds an extra layer of protection for any client information that comes up in conversation. Provide the direct path: *Settings > Privacy > "Improve Claude" toggle*.

3. **Client name exclusion (optional).** For additional privacy, the user may choose to exclude client names from the database entirely, storing only client ID numbers and matter ID numbers. Explain the trade-off clearly: if names are excluded, Claude will not be able to recognize client names mentioned in conversation or tasks — the user would need to refer to clients by their ID numbers instead. Ask the user whether they want to include or exclude client names.

If the user chooses to exclude names, record this preference — it will be saved to `coclerk.json` in the next step as `exclude_client_names: true`. When this flag is `true`, any import workflow must skip the client name column and store `NULL` in `clients.name`.

## Step 5 — Create or update coclerk.json

Resolve the path `AppData\Roaming\Coclerk\coclerk.json` relative to the current user's home directory (do not hardcode any username). Create the folder if it doesn't exist.

Write or update the config file:

```json
{
  "version": 1,
  "database": {
    "folder": "<full path to the folder the user selected>",
    "filename": "<database name from Step 1>"
  },
  "accounting": {
    "system": "<accounting system from Step 3>"
  },
  "exclude_client_names": false
}
```

Set `exclude_client_names` to `true` if the user opted to exclude client names in Step 4.

## Step 6 — Create the database

Using the folder and filename from the config, create the SQLite database and run the schema from practice-data SKILL.md.

Tell the user: "Your database has been created at `<folder>\<filename>`. You're all set."

## Step 7 — Return to the calling skill

Initialization is complete. Hand control back to whichever skill triggered practice-data. That skill can now proceed with its normal workflow.
