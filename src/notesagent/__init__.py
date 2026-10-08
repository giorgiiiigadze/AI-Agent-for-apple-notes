# Re-export main so the console command in pyproject.toml can launch the app.
from .main import main

if __name__ == "__main__":
    # Run only when this file is started directly, not when it is imported.
    main()
