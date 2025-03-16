# Dewey project aliases
alias consolidate="PYTHONPATH=$PYTHONPATH:$(pwd)/src uv run python -m dewey.scripts.code_consolidator --report"

# Load oh-my-zsh plugins (add your real plugins here)
plugins=(
    git
    docker
    zsh-autosuggestions
    zsh-syntax-highlighting
)
