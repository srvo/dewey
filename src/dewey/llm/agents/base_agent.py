"""Base agent configuration using smolagents framework."""
from smolagents import CodeAgent, HfApiModel

class DeweyBaseAgent(CodeAgent):
    """Base agent for all Dewey agents using smolagents framework."""
    
    def __init__(self, task_type: str, model_id: str = "Qwen/Qwen2.5-Coder-32B-Instruct"):
        model = HfApiModel(
            model_id=model_id,
            provider="deepinfra",
            temperature=0.3,
            max_tokens=4096
        )
        
        super().__init__(
            model=model,
            tools=self._get_tools(),
            system_prompt=self._get_system_prompt(task_type),
            safe_mode="e2b",
            import_map={
                "dewey": ["analyze_code", "generate_docstring", "improve_content"]
            }
        )

    def _get_tools(self):
        return [
            # Common tools would be defined here
        ]

    def _get_system_prompt(self, task_type: str) -> str:
        prompts = {
            "docstring": """You are an expert at analyzing and generating Python docstrings. 
            Follow Google style guidelines and ensure complete documentation of parameters, 
            return values, and exceptions.""",
            "contact": """You are an expert at contact relationship management. 
            Analyze contact data and make merge decisions based on name, email, 
            and interaction patterns.""",
            "data_ingestion": """You specialize in data structure analysis and schema 
            recommendations. Provide detailed column analysis and table structure 
            suggestions.""",
        }
        return prompts.get(task_type, "You are a helpful AI assistant.")
