import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="MCP Server — Good")

TOOLS = [
    {
        "name": "ping",
        "description": "Returns pong. Useful as a lightweight health check.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "echo",
        "description": "Echoes back the provided message string.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to echo back."
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "get_time",
        "description": "Returns the current UTC timestamp in ISO 8601 format.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

CT = {"Content-Type": "application/json"}


def rpc_ok(id_, result):
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def rpc_err(id_, code, message):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


@app.get("/")
async def health():
    return {"status": "ok", "server": "mcp-server-good", "version": "1.0.0"}


@app.post("/mcp")
async def handle(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(rpc_err(None, -32700, "Parse error"), headers=CT)

    req_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {})

    # Notifications (no id) — acknowledge silently per spec
    if req_id is None:
        return JSONResponse({}, status_code=200, headers=CT)

    # Validate params is an object
    if not isinstance(params, dict):
        return JSONResponse(rpc_err(req_id, -32602, "Invalid params: must be an object"), headers=CT)

    if method == "initialize":
        return JSONResponse(rpc_ok(req_id, {
            "protocolVersion": "2025-03-26",
            "serverInfo": {"name": "mcp-server-good", "version": "1.0.0"},
            "capabilities": {"tools": {}}
        }), headers=CT)

    elif method == "notifications/initialized":
        return JSONResponse({}, status_code=200, headers=CT)

    elif method == "tools/list":
        return JSONResponse(rpc_ok(req_id, {"tools": TOOLS}), headers=CT)

    elif method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments") or {}

        tool = next((t for t in TOOLS if t["name"] == name), None)
        if tool is None:
            return JSONResponse(rpc_err(req_id, -32001, f"Unknown tool: {name}"), headers=CT)

        for r in tool["inputSchema"].get("required", []):
            if r not in args:
                return JSONResponse(
                    rpc_err(req_id, -32602, f"Missing required parameter: {r}"),
                    headers=CT
                )

        if name == "ping":
            content = [{"type": "text", "text": "pong"}]
        elif name == "echo":
            content = [{"type": "text", "text": args.get("message", "")}]
        elif name == "get_time":
            content = [{"type": "text", "text": datetime.datetime.utcnow().isoformat() + "Z"}]
        else:
            content = []

        return JSONResponse(rpc_ok(req_id, {"content": content, "isError": False}), headers=CT)

    else:
        return JSONResponse(rpc_err(req_id, -32601, f"Method not found: {method}"), headers=CT)
