import yaml
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("config/config.yaml")

def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """
    Loads the YAML configuration file.

    Args:
        path: The path to the configuration file.

    Returns:
        A dictionary containing the configuration settings.

    Raises:
        FileNotFoundError: If the config file does not exist.
        Exception: For any other parsing errors.
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"Configuration file not found at '{path}'. "
            f"Please create it by copying 'config/config.yaml.example'."
        )

    try:
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
            # TODO: Add validation for the loaded config structure.
            return config
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred while loading the config: {e}")
        raise
