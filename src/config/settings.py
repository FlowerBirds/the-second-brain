"""
配置管理模块
支持YAML配置文件加载和环境变量覆盖
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml


class Settings:
    """配置管理单例"""

    _instance: Optional["Settings"] = None

    def __new__(cls, config_path: str = "config.yaml"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: str = "config.yaml"):
        if self._initialized:
            return
        self.config_path = config_path
        self._config: dict = {}
        self._load_config()
        self._apply_env_overrides()
        self._initialized = True

    def _load_config(self) -> None:
        """从YAML文件加载配置"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(config_file, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}

    def _apply_env_overrides(self) -> None:
        """环境变量覆盖配置"""
        env_mappings = {
            "OPENAI_API_KEY": ("llm", "api_key"),
            "OPENAI_API_BASE": ("llm", "api_base"),
            "EMBEDDING_API_KEY": ("embedding", "api_key"),
            "EMBEDDING_API_BASE": ("embedding", "api_base"),
        }

        for env_var, path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested(path, value)

    def _set_nested(self, path: tuple, value: Any) -> None:
        """设置嵌套配置值"""
        current = self._config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value

    def _get_nested(self, path: tuple, default: Any = None) -> Any:
        """获取嵌套配置值"""
        current = self._config
        for key in path:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        return current

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项，支持点号访问嵌套值

        Args:
            key: 配置键，支持点号分隔，如 "llm.model"
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split(".")
        value = self._get_nested(tuple(keys), default)

        # 类型转换
        if value is None:
            return default
        return value

    def validate(self) -> bool:
        """验证配置完整性"""
        required_keys = [
            ("embedding", "model"),
            ("chroma", "persist_directory"),
            ("chroma", "collection_name"),
            ("llm", "model"),
        ]

        for key_path in required_keys:
            if self._get_nested(key_path) is None:
                raise ValueError(f"缺少必需配置: {'.'.join(key_path)}")

        return True

    @property
    def config(self) -> dict:
        """返回完整配置字典"""
        return self._config.copy()
