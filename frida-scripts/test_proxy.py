#!/usr/bin/env python3
"""
Simple HTTPS proxy to test if Kiro accepts our certificate
This will help verify if --ignore-certificate-errors flag worked
"""

from mitmproxy import http
from mitmproxy.tools.main import mitmdump
import sys

class KiroInterceptor:
    def __init__(self):
        self.request_count = 0
        self.aws_requests = []
    
    def request(self, flow: http.HTTPFlow) -> None:
        """Intercept all requests"""
        self.request_count += 1
        
        # Check if it's an AWS Q request
        if 'amazonaws.com' in flow.request.pretty_host or 'kiro.dev' in flow.request.pretty_host:
            self.aws_requests.append({
                'url': flow.request.pretty_url,
                'method': flow.request.method,
                'host': flow.request.pretty_host,
                'path': flow.request.path
            })
            
            print(f"\n{'='*60}")
            print(f"[AWS REQUEST #{len(self.aws_requests)}]")
            print(f"{'='*60}")
            print(f"Method: {flow.request.method}")
            print(f"Host: {flow.request.pretty_host}")
            print(f"Path: {flow.request.path}")
            print(f"URL: {flow.request.pretty_url}")
            
            # Print headers
            print(f"\nHeaders:")
            for k, v in flow.request.headers.items():
                if k.lower() in ['authorization', 'x-amz-target', 'content-type', 'user-agent']:
                    print(f"  {k}: {v}")
            
            # Print body if present
            if flow.request.content:
                print(f"\nBody ({len(flow.request.content)} bytes):")
                try:
                    body = flow.request.text
                    if len(body) > 500:
                        print(f"  {body[:500]}...")
                    else:
                        print(f"  {body}")
                except:
                    print(f"  [Binary content]")
            
            print(f"{'='*60}\n")
    
    def response(self, flow: http.HTTPFlow) -> None:
        """Intercept all responses"""
        if 'amazonaws.com' in flow.request.pretty_host or 'kiro.dev' in flow.request.pretty_host:
            print(f"\n[AWS RESPONSE]")
            print(f"Status: {flow.response.status_code}")
            print(f"URL: {flow.request.pretty_url}")
            
            if flow.response.content:
                print(f"Body ({len(flow.response.content)} bytes):")
                try:
                    body = flow.response.text
                    if len(body) > 500:
                        print(f"  {body[:500]}...")
                    else:
                        print(f"  {body}")
                except:
                    print(f"  [Binary content]")
            print()

addons = [KiroInterceptor()]

if __name__ == "__main__":
    import sys
    
    # Get port from command line or use default
    port = 9999
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            port = 9999
    
    print("\n" + "="*60)
    print("Kiro HTTPS Proxy Test")
    print("="*60)
    print(f"\nListening on port: {port}")
    print("\nThis proxy will intercept and log all Kiro requests.")
    print("Specifically watching for:")
    print("  - q.*.amazonaws.com (AWS Q API)")
    print("  - *.kiro.dev (Kiro services)")
    print("\nSetup:")
    print("  1. Run this script")
    print(f"  2. Launch Kiro with: --proxy-server=\"127.0.0.1:{port}\"")
    print("  3. Use AI features in Kiro")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")
    
    # Run mitmproxy
    sys.argv = ['mitmdump', '-s', __file__, '--listen-port', str(port)]
    mitmdump()
