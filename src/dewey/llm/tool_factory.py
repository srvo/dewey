
# Refactored from: tool_factory
# Date: 2025-03-16T16:19:11.913767
# Refactor Version: 1.0
from __future__ import annotations

import importlib
import os
from typing import TYPE_CHECKING

import yaml  # type: ignore
from llama_index.core.tools.function_tool import FunctionTool

if TYPE_CHECKING:
    from llama_index.core.tools.tool_spec.base import BaseToolSpec


class ToolType:
    LLAMAHUB = "llamahub"
    LOCAL = "local"


class ToolFactory:
    TOOL_SOURCE_PACKAGE_MAP = {
        ToolType.LLAMAHUB: "llama_index.tools",
        ToolType.LOCAL: "app.engine.tools",
    }

    @staticmethod
    def load_tools(tool_type: str, tool_name: str, config: dict) -> list[FunctionTool]:
        source_package = ToolFactory.TOOL_SOURCE_PACKAGE_MAP[tool_type]
        try:
            if "ToolSpec" in tool_name:
                tool_package, tool_cls_name = tool_name.split(".")
                module_name = f"{source_package}.{tool_package}"
                module = importlib.import_module(module_name)
                tool_class = getattr(module, tool_cls_name)
                tool_spec: BaseToolSpec = tool_class(**config)
                return tool_spec.to_tool_list()
            module = importlib.import_module(f"{source_package}.{tool_name}")
            tools = module.get_tools(**config)
            if not all(isinstance(tool, FunctionTool) for tool in tools):
                msg = f"The module {module} does not contain valid tools"
                raise ValueError(
                    msg,
                )
            return tools
        except ImportError as e:
            msg = f"Failed to import tool {tool_name}: {e}"
            raise ValueError(msg)
        except AttributeError as e:
            msg = f"Failed to load tool {tool_name}: {e}"
            raise ValueError(msg)

    @staticmethod
    def from_env(
        map_result: bool = False,
    ) -> dict[str, list[FunctionTool]] | list[FunctionTool]:
        """Load tools from the configured file.

        Args:
        ----
            map_result: If True, return a map of tool names to their corresponding tools.

        Returns:
        -------
            A dictionary of tool names to lists of FunctionTools if map_result is True,
            otherwise a list of FunctionTools.

        """
        tools: dict[str, FunctionTool] | list[FunctionTool] = {} if map_result else []

        if os.path.exists("config/tools.yaml"):
            with open("config/tools.yaml") as f:
                tool_configs = yaml.safe_load(f)
                for tool_type, config_entries in tool_configs.items():
                    for tool_name, config in config_entries.items():
                        loaded_tools = ToolFactory.load_tools(
                            tool_type,
                            tool_name,
                            config,
                        )
                        if map_result:
                            tools.update(  # type: ignore
                                {tool.metadata.name: tool for tool in loaded_tools},
                            )
                        else:
                            tools.extend(loaded_tools)  # type: ignore

        return tools
