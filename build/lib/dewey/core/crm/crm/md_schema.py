import argparse
import yaml

def parse_markdown(file_path):
    """Parse markdown file and return structured schema with statistics."""
    with open(file_path, 'r') as file:
        lines = [line.rstrip('\n') for line in file]

    root = {
        'title': 'Document Root',
        'level': 0,
        'subsections': [],
        'code_blocks': []
    }
    current_stack = [root]
    in_code_block = False
    code_block_lang = None
    total_word_count = 0
    header_counts = {i: 0 for i in range(1, 7)}
    code_languages = {}

    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith('```'):
            if in_code_block:
                # End code block
                current_section = current_stack[-1]
                current_section['code_blocks'].append({
                    'language': code_block_lang or 'plaintext',
                    'content_length': len(code_block_content)
                })
                in_code_block = False
                code_block_lang = None
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
                new_section = {
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

    # Calculate statistics
    stats = {
        'total_headers': sum(header_counts.values()),
        'header_levels': {f'h{i}': count for i, count in header_counts.items() if count > 0},
        'total_code_blocks': sum(code_languages.values()),
        'code_languages': code_languages,
        'estimated_word_count': total_word_count,
        'depth_level': max(current_stack[-1]['level'] for section in current_stack)
    }

    return {
        'structure': root['subsections'],  # Skip root container
        'statistics': stats
    }

def main():
    parser = argparse.ArgumentParser(description='Generate schema from markdown file')
    parser.add_argument('input_file', help='Path to input markdown file')
    parser.add_argument('output_file', help='Path to output YAML file')
    args = parser.parse_args()

    schema = parse_markdown(args.input_file)

    with open(args.output_file, 'w') as f:
        yaml.dump(schema, f, allow_unicode=True, sort_keys=False, width=120)

if __name__ == '__main__':
    main()
