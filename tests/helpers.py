from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_text(name):
    return (FIXTURES / name).read_text()
