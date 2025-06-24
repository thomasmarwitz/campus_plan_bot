import configparser
from pathlib import Path

from loguru import logger

settings_path = Path("campus_plan_bot/settings") / "settings.ini"


class Settings:

    def update_setting(self, key, value):
        config = configparser.ConfigParser()
        config.read(settings_path)

        if "DEFAULT" not in config:
            config["DEFAULT"] = {}

        config["DEFAULT"][key] = str(value)

        with open(settings_path, "w") as f:
            config.write(f)

        logger.debug(f"Updated setting '{key}' to value '{value}'")

    def load_settings(self, key) -> str:
        config = configparser.ConfigParser()
        config.read(settings_path)

        if key not in config["DEFAULT"]:
            logger.warning("No token found for ASR authentication")
            return ""
        else:
            return config["DEFAULT"][key]
