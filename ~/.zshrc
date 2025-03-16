# Dewey project aliases
alias consolidate="PYTHONPATH=\"$PYTHONPATH:\$PWD/src\" uv run python -m dewey.scripts.code_consolidator --report"
alias prd-relocate="PYTHONPATH=\"$PYTHONPATH:\$PWD/src\" uv run python -m dewey.scripts.prd relocate"

# Load oh-my-zsh plugins (add your real plugins here)

# Load oh-my-zsh plugins (add your real plugins here)
plugins=(
    git
    docker
    zsh-autosuggestions
    zsh-syntax-highlighting
)
