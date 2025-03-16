#!/usr/bin/env python3
import logging
import os
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from classification_engine import ClassificationEngine, ClassificationError
from journal_writer import JournalWriter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    if len(sys.argv) < 2:
        try:
            input_lines = []
            while True:
                line = input()
                input_lines.append(line)
        except EOFError:
            feedback = "\n".join(input_lines)
        except KeyboardInterrupt:
            sys.exit(1)

        if not feedback.strip():
            logger.error("No feedback provided")
            sys.exit(1)
    else:
        feedback = " ".join(sys.argv[1:])
    rules_path = Path("import/mercury/classification_rules.json")
    output_dir = Path("import/mercury/journal")

    try:
        engine = ClassificationEngine(rules_path)
        writer = JournalWriter(output_dir)

        logger.info("Processing: '%s'", feedback)
        engine.process_feedback(feedback, writer)

        logger.info("Feedback successfully applied!")
        logger.debug("New overrides: %s", engine.rules["overrides"])

    except ClassificationError as e:
        logger.exception("Validation Error: %s", str(e))
        sys.exit(1)
    except Exception:
        logger.exception("Unexpected error processing feedback")
        sys.exit(2)


if __name__ == "__main__":
    main()
