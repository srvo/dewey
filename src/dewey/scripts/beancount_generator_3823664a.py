import json
from pathlib import Path


def generate_beancount_accounts(rules_path: Path, output_path: Path) -> None:
    """Generate Beancount account open directives from classification rules."""
    with open(rules_path) as f:
        rules = json.load(f)

    accounts = set()
    for category in rules["categories"]:
        # Clean and format account components
        components = []
        for part in category.split(":"):
            # Capitalize first letter of each part
            cleaned = part.strip().title()
            # Replace spaces with hyphens and remove invalid characters
            cleaned = cleaned.replace(" ", "-").replace("_", "-")
            cleaned = "".join([c for c in cleaned if c.isalnum() or c == "-"])
            components.append(cleaned)

        # Join into Beancount account format
        account = ":".join(components)
        accounts.add(account)

    # Write to output file with open directives
    with open(output_path, "w") as f:
        f.write("* Automatically generated from classification_rules.json\n\n")
        for account in sorted(accounts):
            f.write(f"2000-01-01 open {account}\n")


if __name__ == "__main__":
    rules_path = Path("import/mercury/classification_rules.json")
    output_path = Path("import/mercury/accounts.beancount")
    generate_beancount_accounts(rules_path, output_path)
