"""A2UI Schema Manager and BasicCatalog adapter.

Provides A2uiSchemaManager and BasicCatalog compatible with both
a2ui-agent-sdk 0.4.x and >=0.9.x / 0.12.x in any deployment environment.
"""

from typing import Any, Optional


class BasicCatalog:
    """BasicCatalog configuration helper."""

    @staticmethod
    def get_config(version: str = "0.8", examples_path: Optional[str] = None) -> dict[str, Any]:
        return {"version": version, "name": "basic"}


class A2uiSchemaManager:
    """Generates A2UI system prompts for LLM agents."""

    def __init__(
        self,
        version: str = "0.8",
        catalogs: Optional[list[Any]] = None,
        accepts_inline_catalogs: bool = False,
    ):
        self.version = version
        self.catalogs = catalogs or []
        self.accepts_inline_catalogs = accepts_inline_catalogs

    def generate_system_prompt(
        self,
        role_description: str,
        workflow_description: str = "",
        ui_description: str = "",
        client_ui_capabilities: Optional[dict[str, Any]] = None,
        allowed_components: Optional[list[str]] = None,
        allowed_messages: Optional[list[str]] = None,
        include_schema: bool = False,
        include_examples: bool = False,
        validate_examples: bool = False,
    ) -> str:
        # Try native 0.4.x schema manager if available
        try:
            from a2ui.schema.manager import A2uiSchemaManager as _SdkSchemaManager
            from a2ui.basic_catalog.provider import BasicCatalog as _SdkBasicCatalog
            mgr = _SdkSchemaManager(version=self.version, catalogs=[_SdkBasicCatalog.get_config(self.version)])
            return mgr.generate_system_prompt(
                role_description=role_description,
                workflow_description=workflow_description,
                ui_description=ui_description,
                client_ui_capabilities=client_ui_capabilities,
                allowed_components=allowed_components,
                allowed_messages=allowed_messages,
                include_schema=include_schema,
                include_examples=include_examples,
                validate_examples=validate_examples,
            )
        except Exception:
            pass

        # Try >=0.9.x DirectJsonPromptGenerator if available
        try:
            from a2ui.inference_formats.direct_json.prompt_generator import DirectJsonPromptGenerator
            from a2ui.core.basic_catalog.v0_8 import BasicCatalog as _CoreBasicCatalog
            gen = DirectJsonPromptGenerator(catalogs=[_CoreBasicCatalog()])
            schema_instructions = gen.generate()
        except Exception:
            schema_instructions = ""

        parts = [role_description]
        if workflow_description:
            parts.append(f"## Workflow Description:\n{workflow_description}")
        if ui_description:
            parts.append(f"## UI Description:\n{ui_description}")
        if include_schema and schema_instructions:
            parts.append(schema_instructions)

        return "\n\n".join(parts)
