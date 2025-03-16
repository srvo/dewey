import re


def extract_sentences(text):
    """Splits text into sentences."""
    return re.split(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s", text)


def extract_words(sentence):
    """Splits a sentence into words."""
    return re.findall(r"\b\w+\b", sentence.lower())


def count_word_frequency(words):
    """Counts the frequency of each word."""
    word_counts = {}
    for word in words:
        if word in word_counts:
            word_counts[word] += 1
        else:
            word_counts[word] = 1
    return word_counts


def analyze_text(text):
    """Analyzes text to extract sentences, words, and word frequencies."""
    sentences = extract_sentences(text)
    words = []
    for sentence in sentences:
        words.extend(extract_words(sentence))
    word_counts = count_word_frequency(words)
    return sentences, word_counts


def main(text) -> None:
    """Main function to process the text."""
    sentences, word_counts = analyze_text(text)


if __name__ == "__main__":
    text = "This is a sample text. It has multiple sentences! And some words are repeated. This is repeated."
    main(text)
