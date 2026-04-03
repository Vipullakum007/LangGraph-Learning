from langchain_google_genai import GoogleGenerativeAI
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

load_dotenv()

os.environ["LANGCHAIN_PROJECT"] = "Sequential LLM App"


prompt1 = PromptTemplate(
    template='Generate a detailed report on {topic}',
    input_variables=['topic']
)

prompt2 = PromptTemplate(
    template='Generate a 5 pointer summary from the following text \n {text}',
    input_variables=['text']
)

model = GoogleGenerativeAI(model="gemini-2.5-flash" , temperature=0.7)

parser = StrOutputParser()

chain = prompt1 | model | parser | prompt2 | model | parser

config = {
    "tags": ["llm-app", "report-generation", "summarization"],
    "metadata": {
        "model_1": "gemini-2.5-flash",
        "model_1_temperature": 0.7,
        "parser": "StringOutputParser"
    },
    "run_name": "Sequential Chain"
}

result = chain.invoke({'topic': 'Unemployment in India'}, config=config)

print(result)
