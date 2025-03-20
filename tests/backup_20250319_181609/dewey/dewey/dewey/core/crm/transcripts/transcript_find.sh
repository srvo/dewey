#!/bin/bash

# Script to identify potential transcripts in a directory.

# --- Configuration ---
target_directory="${1:-.}"
transcript_extensions=(
  ".txt" ".doc" ".docx" ".odt" ".rtf" ".pdf"
)
transcript_keywords=(
  "transcript" "interview" "meeting" "minutes" "notes" "record" "recording"
  "dialogue" "conversation" "speech" "verbatim" "deposition" "hearing" "q&a" "question" "answer" "statement"
)
min_word_count=150

# --- Script Logic ---
if [ ! -d "$target_directory" ]; then
  echo "Error: Directory '$target_directory' not found." >&2
  exit 1
fi

echo "Searching for potential transcripts in '$target_directory'..."

find "$target_directory" -type f | while read -r file; do
  filename=$(basename "$file")
  extension="${filename##*.}"
  filename_noext="${filename%.*}"

  # --- Check 1: File Extension ---
  is_extension_match=false
  for ext in "${transcript_extensions[@]}"; do
    if [[ "$extension" == "$ext" ]]; then
      is_extension_match=true
      break
    fi
  done

  # --- Check 2: Filename Keywords ---
  is_keyword_match=false
  for keyword in "${transcript_keywords[@]}"; do
     if [[ "$filename_noext" == *"$keyword"* ]] || [[ "$filename_noext" == *$(echo "$keyword" | tr '[:lower:]' '[:upper:]')* ]] || [[ "$filename_noext" == *$(echo "$keyword" | tr '[:upper:]' '[:lower:]')* ]] ; then
      is_keyword_match=true
      break
    fi
  done

  # --- Check 3: Word Count (Independent) ---
  word_count=0
  case "$extension" in
    txt|rtf|odt)
      word_count=$(wc -w < "$file" | tr -d ' ')
      ;;
    doc|docx)
      if command -v textutil &> /dev/null; then
        word_count=$(textutil -convert txt -stdout "$file" | wc -w | tr -d ' ')
      elif command -v antiword &> /dev/null; then
        word_count=$(antiword "$file" 2>/dev/null | wc -w | tr -d ' ')
      elif command -v pandoc &> /dev/null; then
        word_count=$(pandoc -f docx -t plain "$file" 2>/dev/null | wc -w | tr -d ' ')
      else
        word_count=0
      fi
      ;;
    pdf)
      if command -v pdftotext &> /dev/null; then
        word_count=$(pdftotext "$file" - 2>/dev/null | wc -w | tr -d ' ')
      else
        word_count=0
      fi
      ;;
    *)
      word_count=0
      ;;
  esac

  # Check for zero word count *before* comparison.
  is_word_count_sufficient=false
  if [[ "$word_count" -gt 0 ]] && [[ "$word_count" -ge "$min_word_count" ]]; then
    is_word_count_sufficient=true
  fi

  # --- Special Handling for .conf files ---
    if [[ "$extension" == "conf" ]] && ! $is_word_count_sufficient; then
        continue # Skip .conf files unless they have a sufficient word count.
    fi


  # --- Decision Logic (Simplified) ---
  if [[ "$is_extension_match" == "true" ]] || [[ "$is_keyword_match" == "true" ]] || [[ "$is_word_count_sufficient" == "true" ]]; then
    output="Potential transcript: '$file'"
    reasons=()

    if [[ "$is_extension_match" == "true" ]]; then
      reasons+=("extension match ($extension)")
    fi
    if [[ "$is_keyword_match" == "true" ]]; then
      reasons+=("filename keyword match")
    fi
    if [[ "$is_word_count_sufficient" == "true" ]]; then
      reasons+=("word count ($word_count >= $min_word_count)")
    fi

    reason_string=$(IFS=,; echo "${reasons[*]}")
    output+=" (Reasons: $reason_string)"
    echo "$output"
  fi
done

echo "Search complete."
exit 0
