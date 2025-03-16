```python
import argparse
from typing import Any, Dict, List
import yaml


def parse_markdown(file_path: str) -> Dict[str, Any]:
    """Parse a markdown file and return a structured schema with statistics.

    Args:
        file_path: The path to the markdown file.

    Returns:
        A dictionary containing the structure and statistics of the markdown file.
    """
    with open(file_path, 'r') as file:
        lines = [line.rstrip('\n') for line in file]

    return analyze_markdown(lines)


def analyze_markdown(lines: List[str]) -> Dict[str, Any]:
    """Analyze markdown lines to extract structure and statistics.

    Args:
        lines: A list of strings, where each string is a line from the markdown file.

    Returns:
        A dictionary containing the structure and statistics of the markdown content.
    """
    root: Dict[str, Any] = {
        'title': 'Document Root',
        'level': 0,
        'subsections': [],
        'code_blocks': []
    }
    current_stack: List[Dict[str, Any]] = [root]
    in_code_block: bool = False
    code_block_lang: str | None = None
    code_block_content: List[str] = []
    total_word_count: int = 0
    header_counts: Dict[int, int] = {i: 0 for i in range(1, 7)}
    code_languages: Dict[str, int] = {}

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('```'):
            if in_code_block:
                # End code block
                current_section = current_stack[-1]
                current_section['code_blocks'].append({
                    'language': code_block_lang or 'plaintext',
                    'content_length': len(''.join(code_block_content))
                })
                in_code_block = False
                code_block_lang = None
                code_block_content = []
            else:
                # Start code block
                in_code_block = True
                code_block_lang = stripped[3:].strip() or 'plaintext'
                code_block_content = []
                code_languages[code_block_lang] = code_languages.get(code_block_lang, 0) + 1
        elif in_code_block:
            code_block_content.append(line)
        else:
            # Word count (exclude code blocks)
            total_word_count += len(stripped.split())

            if stripped.startswith('#'):
                # Parse header
                level = 0
                while stripped.startswith('#'):
                    level += 1
                    stripped = stripped[1:]
                title = stripped.strip()
                header_counts[level] = header_counts.get(level, 0) + 1

                # Create new section
                new_section: Dict[str, Any] = {
                    'title': title,
                    'level': level,
                    'subsections': [],
                    'code_blocks': []
                }

                # Find appropriate parent
                while current_stack[-1]['level'] >= level:
                    current_stack.pop()

                current_stack[-1]['subsections'].append(new_section)
                current_stack.append(new_section)

    stats = calculate_statistics(header_counts, code_languages, total_word_count, current_stack)

    return {
        'structure': root['subsections'],  # Skip root container
        'statistics': stats
    }


def calculate_statistics(
        header_counts: Dict[int, int],
        code_languages: Dict[str, int],
        total_word_count: int,
        current_stack: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Calculate statistics from the parsed markdown data.

    Args:
        header_counts: A dictionary of header levels and their counts.
        code_languages: A dictionary of code languages and their counts.
        total_word_count: The total word count of the markdown content.
        current_stack: The stack of sections being processed.

    Returns:
        A dictionary containing the calculated statistics.
    """
    return {
        'total_headers': sum(header_counts.values()),
        'header_levels': {f'h{i}': count for i, count in header_counts.items() if count > 0},
        'total_code_blocks': sum(code_languages.values()),
        'code_languages': code_languages,
        'estimated_word_count': total_word_count,
        'depth_level': max(section['level'] for section in current_stack) if current_stack else 0
    }


def main() -> None:
    """Main function to parse markdown and generate a YAML schema."""
    parser = argparse.ArgumentParser(description='Generate schema from markdown file')
    parser.add_argument('input_file', help='Path to input markdown file')
    parser.add_argument('output_file', help='Path to output YAML file')
    args = parser.parse_args()

    schema = parse_markdown(args.input_file)

    with open(args.output_file, 'w') as f:
        yaml.dump(schema, f, allow_unicode=True, sort_keys=False, width=120)


if __name__ == '__main__':
    main()
```
