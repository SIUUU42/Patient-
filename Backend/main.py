from fastapi import FastAPI
from pydantic import BaseModel
from services.history import process_answer

#GETTING fastapi
app=FastAPI()

#class of histories, will contain question and answer of ai, validated using pydantic
class Histories(BaseModel):
    session_id: str
    question_id: str
    answer: str

@app.get('/')
def root():
    return {"message:", "Hermes Backend"}

@app.post("/history/answer")
def answer_history(request: Histories):

    #We basically have P3-b working on the services, which will connect Atulyas AI and Zakis Database
    #Use process_answer function(under p3-b) to fetch the answer
    #Basic Communication between Shivaj and Rudra
    #WIP
    result = process_answer(request.answer)

    return result