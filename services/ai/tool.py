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

@tool 
def followup_handler(query:str):
    '''
    This tool is designed to resturcture the vague or underspecified follow-up query.
    If the query is identified as a follow-up,the tool evaluates whether it is vague or 
    underspecified. In cases where the query lacks clarity, context, or explicit details, 
    the tool restructures and rephrases the query into a clearer and more explicit form 
    that is easier for the LLM to understand and respond to accurately.

    Key responsibilities:
    - Detect if the query is a follow-up question.
    - Identify vague, incomplete, or ambiguous queries.
    - Restructure vague follow-up queries into well-formed, self-contained and detailed queries like shown in example.

    Intended use:
    - To improve conversational continuity and reduce ambiguity.
    - To ensure the LLM receives clear, structured inputs, leading to 
      more accurate and context-aware responses

    Example:
    ---
    - User: "did you do the comedy factory project"
    - Assistant: "Yes"
    - User: "What was the Techstack"
    - Tool → Restructured: "What was the Techstack of comedy factory project"
    '''