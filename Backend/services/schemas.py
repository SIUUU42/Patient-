from pydantic import BaseModel, Field
#class of histories, will contain question and answer of ai, validated using pydantic
class Histories(BaseModel):
    session_id: str = Field(pattern=r"^S\d{4}$")
    question_id: str = Field(pattern=r"^Q\d{3}$")
    answer: str = Field(max_length=500)
    language: str = Field(max_length=2)

class Track(BaseModel):
    track: str=Field(pattern=r"^(ayush|standard)$")