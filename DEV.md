## Install Python 3

OS X
```zsh
# install pyenv
brew install pyenv
# install Python 3
pyenv install 3.9.0
# setup as our global default version for pyenv environments
pyenv global 3.9.0
# check
pyenv version
```

```zsh
# add to .zshrc
echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.zshrc
```

```zsh
# restart the terminal and test
which python
python -V
pip -V
```

## Install Web3.py

```zsh
pip install web3
```