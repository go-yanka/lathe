# G_mcp_helpers — pure JSON-RPC 2.0 / MCP envelope helpers, authored THROUGH the harness (gated+pinned).
# lathe_mcp.py (the stdio server, spine I/O) uses these to frame every response. LLM-independent by nature.
OUT_DIR = "projects/agentic-harness/tools"
MODULE_NAME = "mcp_helpers"
HEADER = ""
GLUE = ""
_ONLY = "Output ONLY the Python function code — no prose, no markdown, no tests. Import inside the function."
FUNCTIONS = [
    {"name": "jsonrpc_result",
     "prompt": ("Write jsonrpc_result(rid, result) -> dict. Return {'jsonrpc': '2.0', 'id': rid, 'result': result}. "
                "Never raise." + "\n" + _ONLY),
     "tests": [
        "assert jsonrpc_result(1, {'ok': True}) == {'jsonrpc': '2.0', 'id': 1, 'result': {'ok': True}}",
        "assert jsonrpc_result('a', []) == {'jsonrpc': '2.0', 'id': 'a', 'result': []}",
        "assert jsonrpc_result(None, 0) == {'jsonrpc': '2.0', 'id': None, 'result': 0}",
     ]},
    {"name": "jsonrpc_error",
     "prompt": ("Write jsonrpc_error(rid, code, message) -> dict. Return {'jsonrpc': '2.0', 'id': rid, "
                "'error': {'code': code, 'message': message}}. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert jsonrpc_error(1, -32601, 'x') == {'jsonrpc': '2.0', 'id': 1, 'error': {'code': -32601, 'message': 'x'}}",
        "assert jsonrpc_error(None, -32000, 'e')['error']['code'] == -32000",
     ]},
    {"name": "tool_text",
     "prompt": ("Write tool_text(text) -> dict, the MCP tools/call result shape: "
                "{'content': [{'type': 'text', 'text': str(text)}]}. None -> text ''. Never raise." + "\n" + _ONLY),
     "tests": [
        "assert tool_text('hi') == {'content': [{'type': 'text', 'text': 'hi'}]}",
        "assert tool_text(None) == {'content': [{'type': 'text', 'text': ''}]}",
        "assert tool_text(42) == {'content': [{'type': 'text', 'text': '42'}]}",
     ]},
]
