import yaml
from pathlib import Path
from src.loader import DataLoader
from src.processor import DataProcessor
from src.indicators import IndicatorBuilder


def load_config(path: str = "config.yml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def print_menu():
    print("\n" + "="*50)
    print("  PP422 — Regional Opportunities in Frontier Industries")
    print("="*50)
    print("  1. Build analysis panel (DataProcessor)")
    print("  2. Build indicators (IndicatorBuilder)")
    print("  3. Descriptive analysis        [coming soon]")
    print("  4. Regression analysis         [coming soon]")
    print("  5. Generate maps               [coming soon]")
    print("  0. Exit")
    print("="*50)


def main():
    config = load_config()

    while True:
        print_menu()
        choice = input("  Select an option: ").strip()

        if choice == "1":
            print("\n[DataProcessor] Building analysis panel...")
            processor = DataProcessor(config)
            processor.build_panel()

        elif choice == "2":
            print("\n[IndicatorBuilder] Building indicators...")
            loader = DataLoader(config)
            processor = DataProcessor(config)
            panel = processor.build_panel()
            builder = IndicatorBuilder(config)
            builder.build_indicators(panel)

        elif choice == "3":
            print("\n[Step 7] Descriptive analysis — coming soon.")

        elif choice == "4":
            print("\n[Step 8] Regression analysis — coming soon.")

        elif choice == "5":
            print("\n[Step 10] Map generation — coming soon.")

        elif choice == "0":
            print("\n  Exiting. Goodbye.\n")
            break

        else:
            print("\n  Invalid option. Please try again.")


if __name__ == "__main__":
    main()