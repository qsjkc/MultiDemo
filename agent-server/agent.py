from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.runnables.history import RunnableWithMessageHistory
from tools import ALL_TOOLS
import os
import logging

logger = logging.getLogger(__name__)

LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
LLM_MODEL = os.environ.get("LLM_MODEL", "doubao-pro-32k")

SYSTEM_PROMPT = """你是一个乐于助人的智能语音助手。你可以：
1. 用简洁自然的口语回答用户的各种问题
2. 使用工具来获取信息（天气、计算、时间等）
3. 回答问题时保持友好、专业的语气

注意：
- 回复要适合语音播报，简短、自然、口语化
- 如果用户问了需要实时信息的问题，主动调用工具获取
- 如果你不知道答案，直接说不知道，不要编造"""


def create_agent():
    llm = ChatOpenAI(
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        streaming=True,
        temperature=0.7,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_functions_agent(llm, ALL_TOOLS, prompt)
    return AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True,
    )


def convert_messages(messages: list) -> list:
    """将 OpenAI 格式消息列表转换为 LangChain 格式"""
    converted = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            converted.append(SystemMessage(content=content))
        elif role == "assistant":
            converted.append(AIMessage(content=content))
        else:
            converted.append(HumanMessage(content=content))
    return converted


executor = create_agent()