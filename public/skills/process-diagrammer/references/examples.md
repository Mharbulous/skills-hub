# Process Diagram Examples

## Minimal Example

Smallest valid diagram - use as starting template:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "File Backup Process",
  "description": "Simple backup workflow",
  "version": "1.0.0",
  "metadata": {
    "createdDate": "2026-02-01",
    "domain": "operations"
  },
  "phases": [
    {
      "id": "phase_1",
      "name": "Backup",
      "description": "Execute backup operations",
      "order": 1,
      "steps": [
        {
          "id": "step_1.1",
          "name": "Select Files",
          "description": "Identify files to backup",
          "order": 1,
          "inputs": [
            { "name": "Source Directory", "type": "directory", "source": "/data/" }
          ],
          "outputs": [
            { "name": "File List", "type": "array", "destination": "memory" }
          ],
          "tools": [],
          "dependencies": []
        },
        {
          "id": "step_1.2",
          "name": "Copy Files",
          "description": "Copy files to backup location",
          "order": 2,
          "inputs": [
            { "name": "File List", "type": "array", "fromStep": "step_1.1" }
          ],
          "outputs": [
            { "name": "Backup Archive", "type": "zip", "destination": "/backups/" }
          ],
          "tools": [],
          "dependencies": ["step_1.1"]
        }
      ]
    }
  ],
  "tools": [],
  "dataFlows": [
    {
      "id": "flow_1",
      "name": "Backup Flow",
      "description": "Files copied to backup location",
      "path": ["/data/", "/backups/"],
      "transformation": "compression",
      "steps": ["step_1.1", "step_1.2"]
    }
  ],
  "dependencyGraph": {
    "edges": [
      { "from": "step_1.1", "to": "step_1.2" }
    ]
  }
}
```

## Parallel Processing Pattern

When steps can execute concurrently:

```json
{
  "parallelExecutionGroups": [
    {
      "groupId": "parallel_1",
      "description": "Process each file type independently",
      "steps": ["step_2.1", "step_2.2", "step_2.3"]
    }
  ],
  "phases": [{
    "steps": [
      {
        "id": "step_2.1",
        "parallelWith": ["step_2.2", "step_2.3"],
        "parallelProcessing": {
          "enabled": true,
          "strategy": "one_agent_per_file"
        }
      }
    ]
  }]
}
```

## Structured Output Schema Pattern

When outputs need explicit structure:

```json
{
  "outputs": [
    {
      "name": "Extracted Records",
      "type": "json",
      "destination": "output/records.json",
      "schema": {
        "type": "array",
        "items": {
          "id": "string",
          "timestamp": "string - ISO 8601",
          "data": "object",
          "metadata": {
            "source": "string",
            "confidence": "number 0-1"
          }
        }
      }
    }
  ]
}
```

## Tool Reference Pattern

Complete tool definition with usage tracking:

```json
{
  "tools": [
    {
      "id": "pdf_extractor",
      "name": "extract_pdf.py",
      "type": "script",
      "location": "scripts/extract_pdf.py",
      "purpose": "Extract text and metadata from PDF files",
      "command": "python scripts/extract_pdf.py --input {input} --output {output}",
      "usedInSteps": ["step_1.3", "step_2.1"]
    },
    {
      "id": "parallel_runner",
      "name": "/swarm",
      "type": "skill",
      "location": ".claude/commands/swarm.md",
      "purpose": "Spawn parallel agents for concurrent processing",
      "usedInSteps": ["step_2.2"]
    }
  ]
}
```

## Folder Structure Output Pattern

When a step creates directory hierarchies:

```json
{
  "outputs": [
    {
      "name": "Project Structure",
      "type": "directory_tree",
      "path": "{project}/",
      "structure": {
        "src": {
          "components": {},
          "utils": {},
          "styles": {}
        },
        "tests": {},
        "docs": {},
        "config": {}
      }
    }
  ]
}
```

## Implementation Status Pattern

Track what's built vs pending:

```json
{
  "implementationStatus": {
    "complete": ["step_1.1", "step_1.2", "step_2.1"],
    "pending": ["step_2.2", "step_2.3"],
    "notStarted": ["step_3.1"]
  }
}
```

## Data Flow Pipeline Pattern

Show transformations across steps:

```json
{
  "dataFlows": [
    {
      "id": "flow_1",
      "name": "Document Processing Pipeline",
      "description": "Raw documents converted to structured data",
      "path": ["input/raw/", "processing/parsed/", "output/structured/"],
      "transformation": "PDF -> JSON -> Database",
      "steps": ["step_1.2", "step_2.1", "step_2.3", "step_3.1"]
    }
  ]
}
```

## Input Traceability Pattern

Link inputs to their source steps:

```json
{
  "inputs": [
    {
      "name": "Validated Records",
      "type": "json",
      "source": "output/validated.json",
      "fromStep": "step_2.4",
      "required": true
    },
    {
      "name": "Configuration",
      "type": "yaml",
      "source": "config/settings.yaml",
      "required": false
    }
  ]
}
```

## Naming Convention Pattern

Document file naming standards:

```json
{
  "inputs": [
    {
      "name": "Invoice PDFs",
      "type": "pdf",
      "source": "invoices/",
      "namingConvention": "YYYY-MM-DD_INV-{number}_{vendor}.pdf"
    }
  ],
  "outputs": [
    {
      "name": "Processed Invoices",
      "type": "json",
      "destination": "processed/",
      "namingConvention": "{original_name}_extracted.json"
    }
  ]
}
```

## Legal Basis Pattern

For compliance-sensitive steps:

```json
{
  "id": "step_2.4",
  "name": "Apply Deemed Admissions",
  "description": "Document facts deemed admitted by operation of law",
  "legalBasis": "Rule 3-8(7)",
  "inputs": [
    { "name": "Default Judgment", "type": "pdf" },
    { "name": "Original Pleading", "type": "pdf" }
  ]
}
```
