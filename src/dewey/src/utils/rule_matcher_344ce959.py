#!/usr/bin/env python3
import re
import sys


def load_rules(rules_file: str) -> list[tuple[str, str]]:
    """Loads rules from the given file.

    Args:
    ----
        rules_file: The path to the rules file.

    Returns:
    -------
        A list of tuples, where each tuple contains the regex pattern and the full rule.

    """
    with open(rules_file) as file:
        return [(line.split("|")[0], line) for line in file.read().splitlines()]


def search_and_print_matches(rules: list[tuple[str, str]], csv_content: str) -> None:
    """Searches for matches in the CSV content based on the given rules and prints the full rule if a match is found.

    Args:
    ----
        rules: A list of tuples, where each tuple contains the regex pattern and the full rule.
        csv_content: The content of the CSV file.

    """
    for re_pattern, _full_rule in rules:
        rex = re.compile(re_pattern)
        if rex.search(csv_content):
            pass


def main(rules_file: str, csv_file: str) -> None:
    """Main function to load rules, read CSV content, and search for matches.

    Args:
    ----
        rules_file: The path to the rules file.
        csv_file: The path to the CSV file.

    """
    rules = load_rules(rules_file)

    with open(csv_file) as file:
        csv_content = file.read()

    search_and_print_matches(rules, csv_content)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
