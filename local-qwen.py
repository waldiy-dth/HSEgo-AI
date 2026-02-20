from fastapi import FastAPI
from pydantic import BaseModel
import ollama
import uvicorn

app = FastAPI(title="The Brain of HSEgo AI")

class Question(BaseModel):
    text: str
    chat_id: int = 0  
history = {}

@app.post("/ask")
async def ask_llm(q: Question):
    if q.chat_id not in history:
        history[q.chat_id] = []     
    
    history[q.chat_id].append({"role": "user", "content": q.text})
    
    response = ollama.chat(
        model='qwen2.5:3b',
        messages=history[q.chat_id]
    )
    
    answer = response['message']['content']
    history[q.chat_id].append({"role": "assistant", "content": answer})
    
    if len(history[q.chat_id]) > 200:
        history[q.chat_id] = history[q.chat_id][-200:]
    return answer


print("активен http://0.0.0.0:8000")
uvicorn.run(app, host="0.0.0.0", port=8000)
