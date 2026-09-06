from pydantic import BaseModel, Field


# class of conversation history
class ConversationHistory(BaseModel):
    role: str
    content: str
    timestamp: str


# class of histories, will contain conversation history, validated using pydantic
class Histories(BaseModel):

    session_id: str = Field(pattern=r"^S\d{4}$")

    user_id: str = Field(pattern=r"^U\d{3}$")

    language: str = Field(max_length=2)

    conversation_history: list[ConversationHistory]


class Track(BaseModel):

    track: str = Field(pattern=r"^(ayush|standard)$")