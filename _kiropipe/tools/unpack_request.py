#!/usr/bin/env python3
"""
Unpack AWS Q Request
Exports a request to readable JSON and Markdown formats
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def unpack_request_to_json(request_num, output_dir=None):
    """Unpack request to organized JSON file"""
    script_dir = Path(__file__).parent.parent
    posted_dir = script_dir / 'debug_logs' / 'interactions' / 'posted'
    
    if output_dir is None:
        output_dir = script_dir / 'debug_logs' / 'interactions' / 'unpacked'
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Read request
    request_file = posted_dir / f'request_{request_num}.json'
    if not request_file.exists():
        print(f"Request {request_num} not found")
        return None
    
    with open(request_file, 'r') as f:
        request_data = json.load(f)
    
    # Parse body
    body = json.loads(request_data['body'])
    
    # Organize data
    conv_state = body.get('conversationState', {})
    current_msg = conv_state.get('currentMessage', {})
    user_input = current_msg.get('userInputMessage', {})
    context = user_input.get('userInputMessageContext', {})
    history = conv_state.get('history', [])
    
    organized = {
        'metadata': {
            'request_number': request_num,
            'conversation_id': conv_state.get('conversationId', ''),
            'agent_task_type': conv_state.get('agentTaskType', ''),
            'chat_trigger_type': conv_state.get('chatTriggerType', ''),
            'model_id': user_input.get('modelId', ''),
            'origin': user_input.get('origin', ''),
            'profile_arn': body.get('profileArn', ''),
            'unpacked_at': datetime.now().isoformat()
        },
        'current_message': {
            'content': user_input.get('content', ''),
            'tool_results': [],
            'tools_available': []
        },
        'conversation_history': [],
        'raw_request': {
            'url': request_data.get('url', ''),
            'headers': request_data.get('headers', {}),
            'body_size': len(request_data.get('body', ''))
        }
    }
    
    # Extract tool results
    for result in context.get('toolResults', []):
        tool_result = {
            'tool_use_id': result.get('toolUseId', ''),
            'status': result.get('status', ''),
            'content': []
        }
        
        # Extract text from content array
        for item in result.get('content', []):
            if isinstance(item, dict) and 'text' in item:
                tool_result['content'].append(item['text'])
            elif isinstance(item, str):
                tool_result['content'].append(item)
        
        organized['current_message']['tool_results'].append(tool_result)
    
    # Extract tools
    for tool in context.get('tools', []):
        tool_spec = tool.get('toolSpecification', tool)
        organized['current_message']['tools_available'].append({
            'name': tool_spec.get('name', ''),
            'description': tool_spec.get('description', ''),
            'input_schema': tool_spec.get('inputSchema', {})
        })
    
    # Extract history
    for item in history:
        if 'userInputMessage' in item:
            user_msg = item['userInputMessage']
            organized['conversation_history'].append({
                'role': 'user',
                'content': user_msg.get('content', ''),
                'model_id': user_msg.get('modelId', ''),
                'origin': user_msg.get('origin', '')
            })
        elif 'assistantResponseMessage' in item:
            assistant_msg = item['assistantResponseMessage']
            organized['conversation_history'].append({
                'role': 'assistant',
                'content': assistant_msg.get('content', '')
            })
    
    # Save JSON
    output_file = output_dir / f'request_{request_num}_unpacked.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(organized, f, indent=2, ensure_ascii=False)
    
    print(f"✓ JSON saved to: {output_file}")
    return organized


def unpack_request_to_markdown(request_num, output_dir=None):
    """Unpack request to readable Markdown file"""
    script_dir = Path(__file__).parent.parent
    posted_dir = script_dir / 'debug_logs' / 'interactions' / 'posted'
    
    if output_dir is None:
        output_dir = script_dir / 'debug_logs' / 'interactions' / 'unpacked'
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Read request
    request_file = posted_dir / f'request_{request_num}.json'
    if not request_file.exists():
        print(f"Request {request_num} not found")
        return None
    
    with open(request_file, 'r') as f:
        request_data = json.load(f)
    
    # Parse body
    body = json.loads(request_data['body'])
    
    # Extract data
    conv_state = body.get('conversationState', {})
    current_msg = conv_state.get('currentMessage', {})
    user_input = current_msg.get('userInputMessage', {})
    context = user_input.get('userInputMessageContext', {})
    history = conv_state.get('history', [])
    
    # Build markdown
    md = []
    
    # Header
    md.append(f"# AWS Q Request #{request_num}")
    md.append("")
    md.append(f"**Unpacked at**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append("")
    
    # Metadata
    md.append("## Metadata")
    md.append("")
    md.append(f"- **Conversation ID**: `{conv_state.get('conversationId', '')}`")
    md.append(f"- **Agent Task Type**: `{conv_state.get('agentTaskType', '')}`")
    md.append(f"- **Chat Trigger**: `{conv_state.get('chatTriggerType', '')}`")
    md.append(f"- **Model ID**: `{user_input.get('modelId', '')}`")
    md.append(f"- **Origin**: `{user_input.get('origin', '')}`")
    md.append(f"- **Profile ARN**: `{body.get('profileArn', '')}`")
    md.append("")
    
    # Statistics
    md.append("## Statistics")
    md.append("")
    md.append(f"- **Request Size**: {len(request_data.get('body', '')):,} bytes")
    md.append(f"- **History Items**: {len(history)}")
    md.append(f"- **Tools Available**: {len(context.get('tools', []))}")
    md.append(f"- **Tool Results**: {len(context.get('toolResults', []))}")
    md.append("")
    
    # Current Message
    md.append("## Current Message")
    md.append("")
    
    content = user_input.get('content', '')
    if content:
        md.append("### User Content")
        md.append("")
        md.append("```")
        md.append(content)
        md.append("```")
        md.append("")
    else:
        md.append("*(No user content - likely a tool result response)*")
        md.append("")
    
    # Tool Results
    tool_results = context.get('toolResults', [])
    if tool_results:
        md.append("### Tool Results")
        md.append("")
        
        for i, result in enumerate(tool_results, 1):
            tool_id = result.get('toolUseId', '')
            status = result.get('status', '')
            
            md.append(f"#### Tool Result #{i}")
            md.append("")
            md.append(f"- **Tool Use ID**: `{tool_id}`")
            md.append(f"- **Status**: `{status}`")
            md.append("")
            
            # Extract content
            content_items = result.get('content', [])
            if content_items:
                md.append("**Content**:")
                md.append("")
                md.append("```")
                for item in content_items:
                    if isinstance(item, dict) and 'text' in item:
                        md.append(item['text'])
                    elif isinstance(item, str):
                        md.append(item)
                md.append("```")
                md.append("")
    
    # Tools Available
    tools = context.get('tools', [])
    if tools:
        md.append("### Tools Available")
        md.append("")
        md.append(f"Total: {len(tools)} tools")
        md.append("")
        
        # Show first 5 in detail
        for i, tool in enumerate(tools[:5], 1):
            tool_spec = tool.get('toolSpecification', tool)
            name = tool_spec.get('name', '')
            desc = tool_spec.get('description', '')
            
            md.append(f"#### {i}. {name}")
            md.append("")
            
            if desc:
                # Truncate long descriptions
                if len(desc) > 200:
                    md.append(f"{desc[:200]}...")
                else:
                    md.append(desc)
                md.append("")
            
            # Show schema
            schema = tool_spec.get('inputSchema', {})
            if schema:
                md.append("<details>")
                md.append("<summary>Input Schema</summary>")
                md.append("")
                md.append("```json")
                md.append(json.dumps(schema, indent=2))
                md.append("```")
                md.append("")
                md.append("</details>")
                md.append("")
        
        if len(tools) > 5:
            md.append(f"*... and {len(tools) - 5} more tools*")
            md.append("")
    
    # Conversation History
    if history:
        md.append("## Conversation History")
        md.append("")
        md.append(f"Total messages: {len(history)}")
        md.append("")
        
        for i, item in enumerate(history, 1):
            if 'userInputMessage' in item:
                user_msg = item['userInputMessage']
                content = user_msg.get('content', '')
                
                md.append(f"### Message #{i} - User")
                md.append("")
                
                # Truncate very long messages
                if len(content) > 1000:
                    md.append("```")
                    md.append(content[:1000])
                    md.append(f"... (truncated, {len(content):,} chars total)")
                    md.append("```")
                else:
                    md.append("```")
                    md.append(content)
                    md.append("```")
                md.append("")
            
            elif 'assistantResponseMessage' in item:
                assistant_msg = item['assistantResponseMessage']
                content = assistant_msg.get('content', '')
                
                md.append(f"### Message #{i} - Assistant")
                md.append("")
                
                # Truncate very long messages
                if len(content) > 1000:
                    md.append("```")
                    md.append(content[:1000])
                    md.append(f"... (truncated, {len(content):,} chars total)")
                    md.append("```")
                else:
                    md.append("```")
                    md.append(content)
                    md.append("```")
                md.append("")
    
    # Raw Request Info
    md.append("## Raw Request Information")
    md.append("")
    md.append(f"- **URL**: `{request_data.get('url', '')}`")
    md.append("")
    md.append("### Headers")
    md.append("")
    md.append("```json")
    md.append(json.dumps(request_data.get('headers', {}), indent=2))
    md.append("```")
    md.append("")
    
    # Save markdown
    output_file = output_dir / f'request_{request_num}_unpacked.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))
    
    print(f"✓ Markdown saved to: {output_file}")
    return output_file


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python unpack_request.py <request_number> [output_dir]")
        print("\nExample: python unpack_request.py 19")
        print("         python unpack_request.py 19 ./output")
        
        # Show available requests
        script_dir = Path(__file__).parent.parent
        posted_dir = script_dir / 'debug_logs' / 'interactions' / 'posted'
        
        if posted_dir.exists():
            requests = sorted(posted_dir.glob('request_*.json'))
            if requests:
                print("\nAvailable requests:")
                for req_file in requests[-10:]:
                    req_num = req_file.stem.split('_')[1]
                    size = req_file.stat().st_size
                    print(f"  - Request #{req_num}: {size:,} bytes")
        
        return
    
    request_num = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"\n{'='*60}")
    print(f"Unpacking Request #{request_num}")
    print(f"{'='*60}\n")
    
    # Unpack to JSON
    print("Generating JSON...")
    json_data = unpack_request_to_json(request_num, output_dir)
    
    if json_data:
        print(f"  - History messages: {len(json_data['conversation_history'])}")
        print(f"  - Tools available: {len(json_data['current_message']['tools_available'])}")
        print(f"  - Tool results: {len(json_data['current_message']['tool_results'])}")
    
    print()
    
    # Unpack to Markdown
    print("Generating Markdown...")
    md_file = unpack_request_to_markdown(request_num, output_dir)
    
    print(f"\n{'='*60}")
    print("✓ Unpacking complete!")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
