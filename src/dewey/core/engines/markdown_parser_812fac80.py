```python
import argparse
from typing import Any, Dict, List, Tuple
import yaml


def parse_markdown(file_path: str) -> Dict[str, Any]:
    """Parse markdown file and return structured schema with statistics.

    Args:
        file_path: Path to the markdown file.

    Returns:
        A dictionary containing the document structure and statistics.
    """
    with open(file_path, 'r') as file:
        lines = [line.rstrip('\n') for line in file]

    root = {
        'title': 'Document Root',
        'level': 0,
        'subsections': [],
        'code_blocks': []
    }
    structure, stats = _process_lines(lines, root)

    return {
        'structure': structure,
        'statistics': stats
    }


def _process_lines(lines: List[str], root: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Processes the lines of the markdown file to extract structure and statistics.

    Args:
        lines: A list of strings, where each string is a line from the markdown file.
        root: The root dictionary for the document structure.

    Returns:
        A tuple containing the document structure (list of subsections) and the statistics dictionary.
    """
    current_stack: List[Dict[str, Any]] = [root]
    in_code_block: bool = False
    code_block_lang: str = None
    code_block_content: List[str] = []
    total_word_count: int = 0
    header_counts: Dict[int, int] = {i: 0 for i in range(1, 7)}
    code_languages: Dict[str, int] = {}

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('```'):
            if in_code_block:
                _end_code_block(current_stack, code_block_lang, code_block_content)
                in_code_block = False
                code_block_lang = None
            else:
                code_block_lang = _start_code_block(stripped, code_languages)
                in_code_block = True
                code_block_content = []
        elif in_code_block:
            code_block_content.append(line)
        else:
            total_word_count += len(stripped.split())

            if stripped.startswith('#'):
                level, title = _parse_header(stripped, header_counts)
                _process_header(current_stack, level, title)

    stats = _calculate_statistics(header_counts, code_languages, total_word_count, current_stack)
    return root['subsections'], stats


def _start_code_block(stripped_line: str, code_languages: Dict[str, int]) -> str:
    """Handles the start of a code block.

    Args:
        stripped_line: The stripped line that starts with '```'.
        code_languages: A dictionary to keep track of code languages.

    Returns:
        The language of the code block.
    """
    code_block_lang = stripped_line[3:].strip() or 'plaintext'
    code_languages[code_block_lang] = code_languages.get(code_block_lang, 0) + 1
    return code_block_lang


def _end_code_block(current_stack: List[Dict[str, Any]], code_block_lang: str, code_block_content: List[str]) -> None:
    """Handles the end of a code block.

    Args:
        current_stack: The stack of sections.
        code_block_lang: The language of the code block.
        code_block_content: A list of strings representing the content of the code block.
    """
    current_section = current_stack[-1]
    current_section['code_blocks'].append({
        'language': code_block_lang or 'plaintext',
        'content_length': len(code_block_content)
    })


def _parse_header(stripped_line: str, header_counts: Dict[int, int]) -> Tuple[int, str]:
    """Parses a header line.

    Args:
        stripped_line: The stripped line that starts with '#'.
        header_counts: A dictionary to keep track of header counts.

    Returns:
        A tuple containing the header level and the title.
    """
    level = 0
    while stripped_line.startswith('#'):
        level += 1
        stripped_line = stripped_line[1:]
    title = stripped_line.strip()
    header_counts[level] = header_counts.get(level, 0) + 1
    return level, title


def _process_header(current_stack: List[Dict[str, Any]], level: int, title: str) -> None:
    """Processes a header line and updates the document structure.

    Args:
        current_stack: The stack of sections.
        level: The header level.
        title: The header title.
    """
    new_section = {
        'title': title,
        'level': level,
        'subsections': [],
        'code_blocks': []
    }

    while current_stack[-1]['level'] >= level:
        current_stack.pop()

    current_stack[-1]['subsections'].append(new_section)
    current_stack.append(new_section)


def _calculate_statistics(header_counts: Dict[int, int], code_languages: Dict[str, int], total_word_count: int,
                          current_stack: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates statistics for the document.

    Args:
        header_counts: A dictionary containing header counts.
        code_languages: A dictionary containing code languages.
        total_word_count: The total word count.
        current_stack: The stack of sections.

    Returns:
        A dictionary containing the calculated statistics.
    """
    stats = {
        'total_headers': sum(header_counts.values()),
        'header_levels': {f'h{i}': count for i, count in header_counts.items() if count > 0},
        'total_code_blocks': sum(code_languages.values()),
        'code_languages': code_languages,
        'estimated_word_count': total_word_count,
        'depth_level': max(section['level'] for section in current_stack) if current_stack else 0
    }
    return stats


def main():
    """Main function to parse arguments and generate schema."""
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
