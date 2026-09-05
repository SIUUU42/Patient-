from pydantic import BaseModel
#class of histories, will contain question and answer of ai, validated using pydantic
class Histories(BaseModel):
    session_id: str
    question_id: str
    answer: str