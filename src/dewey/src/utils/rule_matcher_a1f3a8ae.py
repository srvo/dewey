#!/usr/bin/env python3

import re
import sys


def read_rules(rules_file: str) -> list[tuple[str, str]]:
    """Reads rules from a file and returns them as a list of tuples.

    Each tuple contains the regex pattern and the full rule.

    Args:
    ----
        rules_file: The path to the rules file.

    Returns:
    -------
        A list of tuples, where each tuple contains the regex pattern and the full rule.

    """
    with open(rules_file) as file:
        return [(line.split("|")[0], line) for line in file.read().splitlines()]


def search_and_print_rules(rules: list[tuple[str, str]], csv_content: str) -> None:
    """Searches for patterns in the CSV content and prints matching rules.

    Args:
    ----
        rules: A list of tuples, where each tuple contains the regex pattern and the full rule.
        csv_content: The content of the CSV file.

    """
    for re_pattern, _full_rule in rules:
        rex = re.compile(re_pattern)
        if rex.search(csv_content):
            pass


def read_csv_content(csv_file: str) -> str:
    """Reads the content of a CSV file.

    Args:
    ----
        csv_file: The path to the CSV file.

    Returns:
    -------
        The content of the CSV file as a string.

    """
    with open(csv_file) as file:
        return file.read()


def main(rules_file: str, csv_file: str) -> None:
    """Main function to process rules and CSV file.

    Args:
    ----
        rules_file: The path to the rules file.
        csv_file: The path to the CSV file.

    """
    rules = read_rules(rules_file)
    csv_content = read_csv_content(csv_file)
    search_and_print_rules(rules, csv_content)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
