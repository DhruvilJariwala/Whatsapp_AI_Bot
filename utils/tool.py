from langchain_core.tools import tool

@tool
def switch_state(query:str):
    """
    Use this tool to transfer the conversation from the AI assistant to a human agent or customer support representative.
    Purpose:
    - To switch the conversation flow from automated AI handling to a human-assisted interaction.
    - To ensure the user is connected to a live human when the query requires personal assistance, escalation, or manual intervention.
    - To improve user experience when the AI is not sufficient or the user explicitly requests human support.

    Trigger Conditions:
    - Call this tool whenever the user:
        * Explicitly asks to talk to a human, agent, or representative.
        * Requests live support, customer care, or manual assistance.
        * Expresses frustration or dissatisfaction with automated responses.
        * Asks for escalation or says they want to speak to a real person.
        * Uses phrases such as “connect me to support”, “human help”, “agent please”, etc.

    Non-Trigger Conditions: Queries About Following:
    - General informational questions that the AI can answer.
    - Requests for explanations, summaries, or clarifications.
    - Casual conversation or small talk.
    - Follow-up questions where AI response is adequate.
    - Queries that do not indicate a need for escalation or human involvement.

    Example Queries:
        - "I want to talk to a human"
        - "Connect me to customer support"
        - "Can I speak with a real person?"
        - "This is not helpful, I need an agent"
        - "Transfer this chat to a human"
        - "I want live support"
        - "Please escalate this issue"
    """
    pass
