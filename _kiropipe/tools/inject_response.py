#!/usr/bin/env python3
"""
Inject Response Test
Generates a synthetic AWS Event Stream response and serves it via HTTP
This allows testing if Kiro can properly receive and display our generated responses
"""

import sys
import json
import socket
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.event_stream_encoder import (
    encode_text_chunk,
    encode_tool_use_chunk,
    encode_metering,
    encode_context_usage
)


def find_free_port(start_port=8132, max_attempts=100):
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find free port in range {start_port}-{start_port + max_attempts}")


class ResponseInjector(BaseHTTPRequestHandler):
    """HTTP handler that injects synthetic responses"""
    
    def do_POST(self):
        """Handle POST requests"""
        path = urlparse(self.path).path
        
        if path == '/generateAssistantResponse':
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length)
            
            try:
                request_data = json.loads(request_body)
                
                # Extract user message for context
                conv_state = request_data.get('conversationState', {})
                current_msg = conv_state.get('currentMessage', {})
                user_input = current_msg.get('userInputMessage', {})
                user_content = user_input.get('content', '')
                
                print(f"\n{'='*60}")
                print("[Injector] Received request")
                print(f"{'='*60}")
                print(f"User message: {user_content[:100]}...")
                
                # Generate response based on request type
                response_data = self.generate_response(request_data)
                
                # Send response
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.amazon.eventstream')
                self.send_header('x-amzn-RequestId', 'injector-test-12345')
                self.end_headers()
                
                # Write binary response
                self.wfile.write(response_data)
                
                print(f"[Injector] Sent {len(response_data)} bytes")
                print(f"{'='*60}\n")
                
            except Exception as e:
                print(f"[Injector] Error: {e}")
                import traceback
                traceback.print_exc()
                
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def generate_response(self, request_data):
        """Generate synthetic AWS Event Stream response"""
        # Check if this is a tool result response
        conv_state = request_data.get('conversationState', {})
        current_msg = conv_state.get('currentMessage', {})
        user_input = current_msg.get('userInputMessage', {})
        context = user_input.get('userInputMessageContext', {})
        tool_results = context.get('toolResults', [])
        user_content = user_input.get('content', '')
        
        response_chunks = []
        
        if tool_results:
            # This is a response after tool execution
            print("[Injector] Generating response for tool results")
            
            # Generate a response that acknowledges the tool results
            response_chunks.append(encode_text_chunk("I've received the tool results. "))
            response_chunks.append(encode_text_chunk("Based on the information, "))
            response_chunks.append(encode_text_chunk("everything looks good!"))
        
        elif 'test tool' in user_content.lower() or 'call a tool' in user_content.lower():
            # Generate a response with a tool call
            print("[Injector] Generating response with tool call")
            
            response_chunks.append(encode_text_chunk("I'll help you with that. "))
            response_chunks.append(encode_text_chunk("Let me read the file for you."))
            
            # Generate tool call
            tool_id = "tooluse_test_12345"
            response_chunks.append(encode_tool_use_chunk("readFile", tool_id, '{"path"'))
            response_chunks.append(encode_tool_use_chunk("readFile", tool_id, ': "test.py"}'))
            response_chunks.append(encode_tool_use_chunk("readFile", tool_id, ''))  # End marker
        
        else:
            # Generate a simple text response
            print("[Injector] Generating simple text response")
            
            response_chunks.append(encode_text_chunk("Hello! "))
            response_chunks.append(encode_text_chunk("This is a synthetic response "))
            response_chunks.append(encode_text_chunk("generated by the injection test script. "))
            response_chunks.append(encode_text_chunk("It demonstrates that the AWS Event Stream format "))
            response_chunks.append(encode_text_chunk("is working correctly!"))
        
        # Add usage metrics
        response_chunks.append(encode_metering(0.15))
        response_chunks.append(encode_context_usage(25.5))
        
        # Combine all chunks
        return b''.join(response_chunks)
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def main():
    """Main function"""
    import os
    
    # Get port from environment or find a free one
    port = int(os.environ.get('BRIDGE_PORT', 0))
    if port == 0:
        port = find_free_port()
    
    # Write port to file for auto-detection
    port_file = Path(__file__).parent.parent / 'debug_logs' / '.server_port'
    port_file.parent.mkdir(parents=True, exist_ok=True)
    port_file.write_text(str(port))
    
    print("\n" + "="*60)
    print("Response Injection Test Server")
    print("="*60)
    print(f"\nServer running on: http://localhost:{port}")
    print(f"Endpoint: POST /generateAssistantResponse")
    print("\nTo use this with Kiro:")
    print("1. Set ENABLE_BRIDGE = True in kiropipe.py")
    print(f"2. Set BRIDGE_URL = 'http://localhost:{port}' in kiropipe.py")
    print("3. Run kiropipe.py to launch Kiro")
    print("4. Send a message in Kiro")
    print("\nTest scenarios:")
    print("  - Normal message: 'Hello, how are you?'")
    print("  - Tool call test: 'Please test tool calling'")
    print("\nTo use a specific port:")
    print(f"  set BRIDGE_PORT={port}")
    print(f"  python _kiropipe/tools/inject_response.py")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")
    
    try:
        server = HTTPServer(('localhost', port), ResponseInjector)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n[Injector] Shutting down...")
        server.shutdown()
    finally:
        # Clean up port file
        if port_file.exists():
            port_file.unlink()


if __name__ == '__main__':
    main()
