from workers import DurableObject, Response, WorkerEntrypoint
import json


class MyDurableObject(DurableObject):
  
    def __init__(self, ctx, env):
        super().__init__(ctx, env)
    
    async def say_hello(self, name):
        return f"Hello, {name}!"
    
    async def gen_reply(self,message: str) -> dict:
        return dict({"role":"assistant","content":f"you said {message}"})
    
    async def chat_handler(self,role,message):
        raw = await self.ctx.storage.get("messages")
        if raw is None:
            messages = []
        else:
            messages = json.loads(raw)

        current_message = dict({"role":role, "content": message})
        reply = await self.gen_reply(current_message.get("content"))

        messages.append(current_message)
        messages.append(reply)
        
        await self.ctx.storage.put("messages",json.dumps(messages))
        

        return reply
    
    async def get_history(self):
        raw = await self.ctx.storage.get("messages")

        if raw is None:
            messages = []
        else:
            messages = json.loads(raw)
        
        return messages


class Default(WorkerEntrypoint):
    async def fetch(self, request):

        url = request.url
        method = request.method
       

        # Chat endpoint (no AI yet)
        if method == "POST" and url.endswith("/chat"):
            stub = self.env.MY_DURABLE_OBJECT.getByName("foo")
            try:
                body = await request.json()
            except Exception:
                return Response(
                    json.dumps({"error": "Invalid JSON"}),
                    headers={"content-type": "application/json"},
                    status=400,
                )

            msg = body.get("message")
            if not isinstance(msg, str) or not msg.strip():
                return Response(
                    json.dumps({"error": "`message` must be a non-empty string"}),
                    headers={"content-type": "application/json"},
                    status=400,
                )

            # For now, just echo back
            reply = await stub.chat_handler("user",msg)

            return Response(
                json.dumps({"reply": reply["content"]}),
                headers={"content-type": "application/json"},
            )
        
        if method == "GET" and url.endswith("/history"):
            stub = self.env.MY_DURABLE_OBJECT.getByName("foo")
            messages = await stub.get_history()

            return Response(
                json.dumps({"messages": messages}),
                headers={"content-type": "application/json"},
            )
        
        
        return Response("Not found", status=404)
