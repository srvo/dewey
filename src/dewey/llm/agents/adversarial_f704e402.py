# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:53:33 2025

"""Critical analysis and risk identification agent."""
from .adversarial_agent import AdversarialAgent

async def analyze_risks(proposal: str) -> str:
    """Analyzes potential risks and issues using the new AdversarialAgent."""
    agent = AdversarialAgent()
    return await agent.analyze_risks(proposal)
