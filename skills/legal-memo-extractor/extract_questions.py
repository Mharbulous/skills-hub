#!/usr/bin/env python3
"""
Legal Research Memo Question Extractor

Extracts and indexes research questions from AI-generated legal research memos.
Intelligently filters answer headings from true questions.
"""

import re
import random
from datetime import datetime
from pathlib import Path


def extract_from_memo(file_path):
    """
    Phase 1: Single-Pass Extraction
    
    Extract metadata and all numbered items in a single pass through the file.
    
    Returns:
        tuple: (candidates, jurisdiction, file_size)
    """
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


def is_answer_heading(text):
    """
    Phase 2: Intelligent Filtering
    
    Detect if text is an answer heading rather than a question.
    
    Returns:
        bool: True if answer heading, False if likely a question
    """
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


def validate_extraction(questions, file_path, sample_size=5):
    """
    Phase 3: Quality Validation
    
    Spot-check sample questions for accuracy and check for duplicates.
    
    Returns:
        bool: True if validation passes, False otherwise
    """
    # Check for duplicates
    numbers = [q['number'] for q in questions]
    if len(numbers) != len(set(numbers)):
        print(f"    WARNING: Duplicate question numbers found")
        return False
    
    # Spot-check samples if enough questions
    if len(questions) >= sample_size:
        samples = random.sample(questions, sample_size)
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        for sample in samples:
            # Verify text appears in source (allowing for some formatting variation)
            clean_text = sample['text'].replace('\n', ' ').strip()
            if clean_text not in content and sample['text'] not in content:
                print(f"    WARNING: Text mismatch: {sample['text'][:50]}...")
                return False
    
    return True


def generate_index(all_memos_data):
    """
    Phase 4: Output Generation
    
    Create formatted markdown table with renumbered questions.
    
    Returns:
        str: Markdown formatted index
    """
    output = []
    output.append("# Legal Research Memo Question Index\n\n")
    
    total_questions = sum(len(data['questions']) for data in all_memos_data)
    output.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    output.append(f"**Total Questions:** {total_questions}\n\n")
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


def standard_output_dir(workspace):
    """Return the standard lawyer-facing AI output folder for a workspace."""
    return Path(workspace) / "0. DRAFT" / f"{datetime.now().strftime('%Y-%m-%d')} AI"


def process_legal_memos(memo_directory="/mnt/project/", output_dir=None):
    """
    Complete Workflow: Process all legal research memos and generate question index.
    
    Args:
        memo_directory: Directory containing memo files
        output_dir: Directory for output file. Defaults to the workspace's
            0. DRAFT/YYYY-MM-DD AI folder.
        
    Returns:
        Path: Path to generated index file, or None if failed
    """
    print("=" * 70)
    print("Legal Research Memo Question Extractor")
    print("=" * 70)
    print()
    
    # Find all memo files
    memo_path = Path(memo_directory)
    memo_files = sorted(memo_path.glob("Westlaw_Edge_Canada_*.docx"))
    
    if not memo_files:
        print(f"✗ No memo files found in {memo_directory}")
        print("  Looking for pattern: Westlaw_Edge_Canada_*.docx")
        return None
    
    print(f"Found {len(memo_files)} memo files\n")
    
    all_memos_data = []
    total_questions = 0
    
    for memo_num, file_path in enumerate(memo_files, 1):
        print(f"[{memo_num:2d}/{len(memo_files):2d}] Processing: {file_path.name}")
        
        try:
            # Phase 1: Extract
            candidates, jurisdiction, file_size = extract_from_memo(file_path)
            print(f"    Found {len(candidates)} numbered items")
            
            # Phase 2: Filter
            questions = filter_questions(candidates)
            print(f"    Filtered to {len(questions)} questions")
            
            # Phase 3: Validate
            if validate_extraction(questions, file_path):
                all_memos_data.append({
                    'file_name': file_path.name,
                    'questions': questions,
                    'jurisdiction': jurisdiction,
                    'file_size': file_size
                })
                total_questions += len(questions)
                print(f"    ✓ Validation passed\n")
            else:
                print(f"    ✗ Validation failed\n")
                
        except Exception as e:
            print(f"    ✗ Error: {e}\n")
            continue
    
    # Phase 4: Generate output
    if not all_memos_data:
        print("\n✗ No memos processed successfully")
        return None
    
    print("=" * 70)
    print("Generating Index")
    print("=" * 70)
    print()
    
    output_content = generate_index(all_memos_data)
    
    output_base = Path(output_dir) if output_dir else standard_output_dir(memo_path)
    output_path = output_base / "research_memos_index.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_content)
    
    print(f"✓ Successfully processed {len(all_memos_data)} memos")
    print(f"✓ Extracted {total_questions} questions")
    print(f"✓ Average: {total_questions / len(all_memos_data):.1f} questions per memo")
    print(f"✓ Output saved to: {output_path}")
    print()
    
    return output_path


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract research questions from legal research memos'
    )
    parser.add_argument(
        '--input-dir',
        default='/mnt/project/',
        help='Directory containing memo files (default: /mnt/project/)'
    )
    parser.add_argument(
        '--output-dir',
        default=None,
        help='Directory for output file (default: <input-dir>/0. DRAFT/YYYY-MM-DD AI)'
    )
    
    args = parser.parse_args()
    
    result = process_legal_memos(args.input_dir, args.output_dir)
    
    if result:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())
