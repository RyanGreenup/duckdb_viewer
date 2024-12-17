check:
    ruff format src/*.py
    ruff check src --fix
    pyright src
    ruff format src/*.py
    mypy --strict src
    # vulture src/*.py

