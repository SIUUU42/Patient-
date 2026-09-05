from fastapi import FastAPI
from pydantic import BaseModel
from services.history import process_answer
from services.schemas import Histories
from routes.backend_b import router as backend_b_router

#GETTING fastapi
app=FastAPI()


@app.get('/')
def root():
    return {"message:": "Hermes Backend"}

app.include_router(backend_b_router)
@app.post("/history/answer")

def answer_history(request: Histories):

    #We basically have P3-b working on the services, which will connect Atulyas AI and Zakis Database
    #Use process_answer function(under p3-b) to fetch the answer
    #Basic Communication between Shivaj and Rudra
    #WIP
    result = process_answer(request.session_id, request.question_id, request.answer)

    return result