---
name: legal-memo-extractor
description: Use when extracting or indexing research questions from Westlaw AI-Assisted Research memos (.docx). Trigger on requests to extract questions, create a question index, or catalog/organize multiple legal research memo files.
---

# Legal Research Memo Question Extractor

Extract and index research questions from AI-generated legal research memos with intelligent filtering to distinguish questions from answer headings.

## Critical File Format Details

### The Gotcha: Plain Text Masquerading as Word

Source files have `.docx` extension but are **plain text files** using pipe-delimited table formatting:

```
| 1\. If smoke from an adjacent strata is leaking into another strata, |
| how bad does it have to be to get an urgent temporary injunction?     |
+-----------------------------------------------------------------------+
```

**Key detail:** Numbers use backslash escape: `1\.` not `1.`

### The Main Challenge: Answer Headings Look Like Questions

Both questions and answer section headings use the same numbered pattern:

```
Question:        | 2\. When a complaint is submitted to the strata...
Answer heading:  | 2\. Procedural Requirements: Before imposing a fine...
```

Both match `| NUMBER\. text |` so you cannot simply extract all numbered items.

## Distinguishing Questions from Answer Headings

### Answer Heading Characteristics

1. **Colon pattern**: Text before first `:` (<100 chars) contains heading keywords
2. **Ends with colon**: Line ends with `:` (section heading style)
3. **Citation-heavy**: Multiple `](())` or `..]()` markers indicate answer text
4. **Heading keywords**:
   - Procedural Requirements
   - Authorization
   - Case Law
   - Mandatory Duty
   - Reasonable Enforcement
   - Legal Consequences
   - Duty of the Strata
   - Owner's Rights and Remedies
   - Implied Covenants
   - Misrepresentation
   - Lease Provisions
   - Actionable Nuisance

### True Questions

- Often end with `?`
- Don't follow heading patterns
- Span multiple lines until separator `+---+` or answer indicators like "To ", "Under ", "Yes", "The "
- Are dispersed throughout the document (not in a single section)

## Implementation

### Phase 1: Single-Pass Extraction

```python
import re
from pathlib import Path

def extract_from_memo(file_path):
    """Extract metadata and all numbered items in single pass."""
    
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    
    # Extract jurisdiction from first 10 lines
    jurisdiction = "Unknown"
    for line in lines[:10]:
        if "**Jurisdictions:**" in line:
            jurisdiction = line.split("**Jurisdictions:**")[1].strip()
            break
    
    # Calculate file size
    file_size = Path(file_path).stat().st_size
    
    # Scan for numbered pattern: | NUMBER\. text |
    numbered_pattern = re.compile(r'^\|\s*(\d+)\\\.\s+(.+?)\s*\|$')
    
    candidates = []
    i = 0
    while i < len(lines):
        match = numbered_pattern.match(lines[i].strip())
        if match:
            number = match.group(1)
            text_parts = [match.group(2)]
            
            # Continue reading subsequent lines for complete text
            j = i + 1
            while j < len(lines):
                line = lines[j].strip()
                
                # Stop at separator
                if line.startswith('+---') or line.startswith('|---'):
                    break
                
                # Stop at answer indicators
                if any(line.startswith(prefix) for prefix in ['| To ', '| Under ', '| Yes', '| The ', '| A ', '| In ']):
                    break
                
                # Stop if citation-heavy
                if '..]()' in line or line.count('](()') > 1:
                    break
                
                # Continue if it's a table row
                if line.startswith('|') and line.endswith('|'):
                    text_parts.append(line.strip('| '))
                    j += 1
                else:
                    break
            
            full_text = ' '.join(text_parts).strip()
            candidates.append({
                'number': number,
                'text': full_text,
                'line_index': i
            })
            i = j
        else:
            i += 1
    
    return candidates, jurisdiction, file_size
```

### Phase 2: Intelligent Filtering

```python
def is_answer_heading(text):
    """Detect if text is an answer heading, not a question."""
    
    # Filter 2.1: Detect answer headings with colon
    if ':' in text:
        before_colon = text.split(':')[0]
        if len(before_colon) < 100:
            heading_keywords = [
                'Procedural Requirements', 'Authorization', 'Case Law',
                'Mandatory Duty', 'Reasonable Enforcement', 'Legal Consequences',
                'Duty of the Strata', "Owner's Rights and Remedies",
                'Implied Covenants', 'Misrepresentation', 'Lease Provisions',
                'Actionable Nuisance', 'Duty of', 'Rights and', 'Requirements'
            ]
            if any(keyword.lower() in before_colon.lower() for keyword in heading_keywords):
                return True
    
    # Filter 2.2: Remove citation fragments
    if text.startswith('..]()') or text[:20].count('..]()') > 0:
        return True
    if text.count('](()') > 2 or text.count('..]()') > 1:
        return True
    
    # Filter 2.3: Remove too-short entries
    if len(text) < 30:
        return True
    
    # Filter 2.4: Remove entries ending with colon
    if text.strip().endswith(':'):
        return True
    
    # Filter 2.5: Remove follow-up instructions
    if 'Research option' in text or 'research option' in text:
        return True
    
    return False

def filter_questions(candidates):
    """Apply intelligent filtering to extract true questions."""
    questions = []
    
    for candidate in candidates:
        if not is_answer_heading(candidate['text']):
            questions.append(candidate)
    
    return questions
```

### Phase 3: Quality Validation

```python
def validate_extraction(questions, file_path, sample_size=5):
    """Spot-check sample questions for accuracy."""
    
    import random
    
    # Check for duplicates
    numbers = [q['number'] for q in questions]
    if len(numbers) != len(set(numbers)):
        print(f"WARNING: Duplicate question numbers in {file_path}")
        return False
    
    # Spot-check samples
    if len(questions) > sample_size:
        samples = random.sample(questions, sample_size)
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        for sample in samples:
            # Verify text appears in source
            if sample['text'] not in content:
                print(f"WARNING: Text mismatch in {file_path}: {sample['text'][:50]}...")
                return False
    
    return True
```

### Phase 4: Output Generation

```python
def generate_index(all_memos_data):
    """Create formatted markdown table with renumbered questions."""
    
    output = []
    output.append("# Legal Research Memo Question Index\n")
    output.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    output.append(f"**Total Questions:** {sum(len(data['questions']) for data in all_memos_data)}\n")
    output.append(f"**Total Memos:** {len(all_memos_data)}\n\n")
    
    output.append("| Memo/Question # | Research Question | Jurisdiction | File Size |\n")
    output.append("|----------------|-------------------|--------------|------------|\n")
    
    for memo_num, memo_data in enumerate(all_memos_data, 1):
        for q_num, question in enumerate(memo_data['questions'], 1):
            # Escape pipe characters in question text
            escaped_text = question['text'].replace('|', '\\|')
            
            # Format file size
            size_kb = memo_data['file_size'] / 1024
            size_str = f"{size_kb:.1f} KB"
            
            output.append(
                f"| {memo_num}.{q_num} | {escaped_text} | "
                f"{memo_data['jurisdiction']} | {size_str} |\n"
            )
    
    return ''.join(output)
```

### Complete Workflow

```python
from datetime import datetime
from pathlib import Path

def standard_output_dir(workspace):
    """Return the standard lawyer-facing AI output folder for a workspace."""
    return Path(workspace) / "0. DRAFT" / f"{datetime.now().strftime('%Y-%m-%d')} AI"

def process_legal_memos(memo_directory="/mnt/project/"):
    """Process all legal research memos and generate question index."""
    
    # Find all memo files
    memo_files = sorted(Path(memo_directory).glob("Westlaw_Edge_Canada_*.docx"))
    
    if not memo_files:
        print("No memo files found. Looking for pattern: Westlaw_Edge_Canada_*.docx")
        return None
    
    print(f"Found {len(memo_files)} memo files")
    
    all_memos_data = []
    total_questions = 0
    
    for file_path in memo_files:
        print(f"Processing: {file_path.name}")
        
        try:
            # Phase 1: Extract
            candidates, jurisdiction, file_size = extract_from_memo(file_path)
            
            # Phase 2: Filter
            questions = filter_questions(candidates)
            
            # Phase 3: Validate
            if validate_extraction(questions, file_path):
                all_memos_data.append({
                    'file_name': file_path.name,
                    'questions': questions,
                    'jurisdiction': jurisdiction,
                    'file_size': file_size
                })
                total_questions += len(questions)
                print(f"  ✓ Extracted {len(questions)} questions")
            else:
                print(f"  ✗ Validation failed")
                
        except Exception as e:
            print(f"  ✗ Error processing {file_path.name}: {e}")
            continue
    
    # Phase 4: Generate output
    if all_memos_data:
        output_content = generate_index(all_memos_data)
        
        output_path = standard_output_dir(memo_directory) / "research_memos_index.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        print(f"\n✓ Successfully processed {len(all_memos_data)} memos")
        print(f"✓ Extracted {total_questions} questions")
        print(f"✓ Output saved to: {output_path}")
        
        return output_path
    else:
        print("\n✗ No memos processed successfully")
        return None

# Execute
if __name__ == "__main__":
    result = process_legal_memos()
```

## Usage Instructions

1. **Verify file location**: Confirm memo files are in `/mnt/project/` (or adjust path)
2. **Run extraction**: Execute the complete workflow script
3. **Review output**: Check `{workspace}/0. DRAFT/YYYY-MM-DD AI/research_memos_index.md`
4. **Validate results**: 
   - Expected: 1-6 questions per memo (typical range)
   - No duplicate question numbers within memos
   - No answer headings in output
   - Questions numbered as 1.1, 1.2, 2.1, 2.2, etc.

## Expected Output Format

```markdown
| Memo/Question # | Research Question | Jurisdiction | File Size |
|----------------|-------------------|--------------|-----------|
| 1.1 | If smoke from an adjacent strata... | British Columbia | 45.2 KB |
| 1.2 | When a complaint is submitted... | British Columbia | 45.2 KB |
| 2.1 | What are the procedural requirements... | British Columbia | 38.7 KB |
```

## Success Criteria

- All memos in directory processed successfully
- Questions per memo: typically 1-6 (varies by memo complexity)
- Zero duplicate question numbers per memo
- 100% exact text match in spot-checks
- No answer headings included
- No citation fragments included
- Proper escaping (`|` → `\|` in question text)
