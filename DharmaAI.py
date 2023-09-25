import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.agents import ZeroShotAgent, Tool, AgentExecutor
from langchain.memory import ConversationBufferWindowMemory
from langchain.memory.chat_message_histories import RedisChatMessageHistory
from langchain import OpenAI, LLMChain
import openai
from dotenv import load_dotenv
import os
from langchain.utilities import SerpAPIWrapper
from datetime import datetime
import requests

load_dotenv()
openai.api_key=st.secrets["OPENAI_API_KEY"]
serpapikey=st.secrets["SERPAPI_API_KEY"]
calendlyapi=st.secrets['calendly_api']
llm = ChatOpenAI(temperature=0)
llm2=OpenAI(temperature=0)
message_history = RedisChatMessageHistory(
url=st.secrets["redis_url"], ttl=600, session_id="username"
)

def consult():
    now = datetime.now()
    startime=str(now)
    nyear=int(startime[:4])+1
    endtime=str(nyear)+startime[4:]
    url = "https://api.calendly.com/event_type_available_times"

    querystring = {"event_type":"https://api.calendly.com/event_types/test","start_time":startime,"end_time":endtime}

    headers = {
        "Content-Type": "application/json",
        "Authorization": calendlyapi
    }

    response = requests.request("GET", url, headers=headers, params=querystring)

    return (response.text["collection"])

def main():
    search=SerpAPIWrapper()
    tools = [
    Tool(
    name="Google Search",
    func=search.run,
    description="Useful for when you need to answer questions related to the law. Input should be a fully formed question.",
    ),
    # Tool(name="human",func=get_input(),description="Useful when asked questions with little context")
    ]

    prefix = """You are a friendly conversational bot who can answer Indian legal questions. if you dont know the answer return your question to the user. You have access to the following tools:"""
    suffix = """Begin!"

    {chat_history}
    Question: {input}
    {agent_scratchpad}
    """

    prompt = ZeroShotAgent.create_prompt(
        tools,
        prefix=prefix,
        suffix=suffix,
        input_variables=["input", "chat_history", "agent_scratchpad"],
    )

    if len(message_history.messages)>10:
        message_history.clear()

    memory = ConversationBufferWindowMemory(k=10,
        memory_key="chat_history", chat_memory=message_history
    )

    llm_chain = LLMChain(llm=llm, prompt=prompt)
    agent = ZeroShotAgent(llm_chain=llm_chain, tools=tools, verbose=True)
    agent_chain = AgentExecutor.from_agent_and_tools(
        agent=agent, tools=tools, verbose=True, memory=memory
    )

    def ask(input: str) -> str:
        print("-- Serving request for input: %s" % input)
        try:
            response= agent_chain.run(input)
        except Exception as e:
            response = str(e)
            if response.startswith("Could not parse LLM output: `"):
                response = response.removeprefix("Could not parse LLM output: `").removesuffix("`")
        return response

    tmp=None

    query=st.text_input(" ",placeholder="Hi, I'm DharmaAI bot. How may I help you?",max_chars=1000)
    if query:
        message_history.add_user_message(query)
        if tmp != None:
            query=tmp

        if ("help" or "consult" or "lawyer") in query.lower():
            message_history.add_ai_message("May I book a consultation for you with our top consultants?")
            tmp=st.text_input("May I book a consultation for you with our top consultants?")
            if ('yes' or 'sure' or 'yeah') in tmp.lower():
                res=consult()
                st.write("Please select your preferable timeslot from below or visit https://calendly.com/shrivastavanolo/test to book a consultation")
                for i in res:
                    dt=datetime(i['scheduling_url'])
                    date_string = dt.strftime("%B %d, %Y %H:%M")
                    st.write(i['start_time'],date_string)    
            tmp=None


        elif ("agent" or "talk to agent" or "connect me") in query.strip().lower():
            message_history.add_ai_message("I will shortly connect you to a live agent")
            st.write("I will shortly connect you to a live agent")


        elif "bye" in query.strip().lower():
            message_history.add_ai_message("Thanks for talking to us. How was your experience?")
            st.write("Thanks for talking to us. How was your experience?")
            message_history.clear()



        elif "thank" in query.strip().lower():
            message_history.add_ai_message("Thanks for talking to us. How was your experience?")
            st.write("Thanks for talking to us. How was your experience?")
            message_history.clear()


        elif "AI:" in query.strip().lower():
            ind=res.index("AI:")
            tmp=st.text_input(res[ind:],placeholder="Type here",max_chars=1000)
            message_history.add_ai_message(res[ind:])
            message_history.add_user_message(tmp)


        else:
            res=ask(query)
            if "Question:" in res:
                ind=res.index("Question:")
                tmp=st.text_input(res[ind:],placeholder="Type here",max_chars=1000)
                message_history.add_ai_message(res[ind:])
                message_history.add_user_message(tmp)
            elif ((res=='None') or ("None:" in res)):
                tmp=st.text_input("Should I schedule a consultation for you?",placeholder="Type here",max_chars=1000)
                message_history.add_ai_message("Should I schedule a consultation for you?")
                message_history.add_user_message(tmp)

            else:
                st.write(res)
                message_history.add_ai_message(res)

if __name__=='__main__':
    main()
