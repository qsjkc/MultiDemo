from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import uuid
import time
import logging
import os

from agent import executor, convert_messages

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Server for Volcano RTC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AGENT_API_KEY = os.environ.get("AGENT_API_KEY", "agent-secret-key")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-server"}


@app.post("/chat")
async def chat(request: Request):
    auth = request.headers.get("Authorization", "")
    expected_auth = f"Bearer {AGENT_API_KEY}"
    if auth and auth != expected_auth and AGENT_API_KEY != "agent-secret-key":
        logger.warning("认证失败: %s", auth[:20])
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    messages = body.get("messages", [])
    stream = body.get("stream", True)
    user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_msg = msg.get("content", "")
            break

    if not user_msg:
        raise HTTPException(status_code=400, detail="No user message found")

    if not stream:
        try:
            result = executor.invoke({"input": user_msg})
            return JSONResponse(content={
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": result.get("output", "")}
                }]
            })
        except Exception as e:
            logger.error("同步调用失败: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    async def generate():
        request_id = str(uuid.uuid4())
        created = int(time.time())

        try:
            async for event in executor.astream_events(
                {"input": user_msg},
                version="v2",
            ):
                kind = event.get("event", "")
                if kind == "on_chat_model_stream":
                    chunk_data = event.get("data", {}).get("chunk", None)
                    if chunk_data is None:
                        continue
                    content = chunk_data.content if hasattr(chunk_data, "content") else ""
                    if not content:
                        continue
                    sse_obj = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": "agent-v1",
                        "choices": [{
                            "index": 0,
                            "delta": {"content": content},
                            "finish_reason": None,
                        }],
                    }
                    yield f"data: {json.dumps(sse_obj, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error("流式调用失败: %s", e)
            sse_obj = {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": "agent-v1",
                "choices": [{
                    "index": 0,
                    "delta": {"content": f"抱歉，处理出错了: {str(e)[:100]}"},
                    "finish_reason": "stop",
                }],
            }
            yield f"data: {json.dumps(sse_obj, ensure_ascii=False)}\n\n"

        final_obj = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": "agent-v1",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(final_obj, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))