import sys
try:
    import fastapi
    import sqlalchemy
    import uvicorn
    import pydantic
    print("SUCCESS: All core dependencies are available.")
    print(f"Python version: {sys.version}")
    print(f"SQLAlchemy version: {sqlalchemy.__version__}")
except ImportError as e:
    print(f"FAILURE: Missing dependency: {e.name}")
    print(f"Current Python executable: {sys.executable}")
    print("\nHELP: It looks like you are not using the correct environment.")
    print("Please activate your conda environment using:")
    print("   conda activate test")
