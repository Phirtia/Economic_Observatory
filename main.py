from src.loader import load_config
from src.processor import DataProcessor


def main():
    config = load_config()
    processor = DataProcessor(config)
    processor.build_panel()


if __name__ == "__main__":
    main()