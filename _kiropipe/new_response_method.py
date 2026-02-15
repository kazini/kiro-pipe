# New response method implementation for KiroInterceptor

def response(self, flow: http.HTTPFlow) -> None:
    """Intercept all responses"""
    
    # Inject custom models into ListAvailableModels response
    if 'ListAvailableModels' in flow.request.path and flow.response.status_code == 200:
        try:
            response_data = json.loads(flow.response.text)
            
            if DEBUG_MODE_ENABLED:
                print(f"\n{Fore.CYAN}{'='*60}")
                print(f"{Style.BRIGHT} [INJECTING CUSTOM MODELS]{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Original Kiro models: {len(response_data.get('models', []))}{Style.RESET_ALL}")
            
            # Track Kiro's original model IDs
            if 'models' in response_data:
                for model in response_data['models']:
                    self.kiro_model_ids.add(model.get('modelId'))
                
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.YELLOW}Tracked Kiro model IDs: {len(self.kiro_model_ids)}{Style.RESET_ALL}")
                
                # Get template from first Kiro model
                template_model = response_data['models'][0] if response_data['models'] else {}
                
                custom_models_added = []
                
                # 1. Inject models from config
                for provider_name in CONFIG.get_enabled_providers():
                    if provider_name == 'kiro':
                        continue  # Skip Kiro's own models
                    
                    provider_config = CONFIG.get_provider_config(provider_name)
                    models = provider_config.get('models', [])
                    
                    for model in models:
                        model_id = model.get('name', 'unknown')
                        model_name = model.get('alias', [model.get('name', 'Unknown')])[0] if model.get('alias') else model.get('name', 'Unknown')
                        
                        custom_model = {
                            "modelId": model_id,
                            "modelName": model_name,
                            "description": model.get('description', f"Custom {provider_name} model"),
                            "promptCaching": template_model.get('promptCaching', {
                                "maximumCacheCheckpointsPerRequest": 4,
                                "minimumTokensPerCacheCheckpoint": 1024,
                                "supportsPromptCaching": True
                            }),
                            "rateMultiplier": 1.0,
                            "rateUnit": "Credit",
                            "supportedInputTypes": ["TEXT", "IMAGE"],
                            "tokenLimits": template_model.get('tokenLimits', {
                                "maxInputTokens": 200000,
                                "maxOutputTokens": None
                            })
                        }
                        
                        response_data['models'].append(custom_model)
                        self.custom_model_ids.add(model_id)
                        custom_models_added.append(model_name)
                
                # 2. Inject dummy test models (debug mode only)
                if DEBUG_MODE_ENABLED:
                    dummy_file = KIROPIPE_DIR / 'devtools' / 'dummy_models.json'
                    if dummy_file.exists():
                        try:
                            dummy_data = json.loads(dummy_file.read_text())
                            dummy_models = dummy_data.get('models', [])
                            
                            for dummy_model in dummy_models:
                                # Validate required fields
                                if 'modelId' in dummy_model and 'modelName' in dummy_model:
                                    response_data['models'].append(dummy_model)
                                    self.custom_model_ids.add(dummy_model['modelId'])
                                    custom_models_added.append(dummy_model['modelName'])
                                else:
                                    print(f"{Fore.YELLOW}[WARNING] Dummy model missing required fields (modelId, modelName){Style.RESET_ALL}")
                            
                            if dummy_models:
                                print(f"{Fore.CYAN}Loaded {len(dummy_models)} dummy test model(s){Style.RESET_ALL}")
                        except json.JSONDecodeError:
                            print(f"{Fore.YELLOW}[WARNING] dummy_models.json exists but contains invalid JSON{Style.RESET_ALL}")
                        except Exception as e:
                            print(f"{Fore.YELLOW}[WARNING] Error loading dummy models: {e}{Style.RESET_ALL}")
                
                # Update response
                if custom_models_added:
                    if DEBUG_MODE_ENABLED:
                        print(f"{Fore.GREEN}Injected {len(custom_models_added)} custom model(s):{Style.RESET_ALL}")
                        for model_name in custom_models_added:
                            print(f"  - {Fore.CYAN}{model_name}{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}Total models: {len(response_data['models'])}{Style.RESET_ALL}")
                    
                    modified_json = json.dumps(response_data).encode('utf-8')
                    flow.response.content = modified_json
                    flow.response.headers['content-length'] = str(len(modified_json))
                    
                    if DEBUG_MODE_ENABLED:
                        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
                else:
                    if DEBUG_MODE_ENABLED:
                        print(f"{Fore.YELLOW}No custom models to inject{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
            
        except json.JSONDecodeError:
            if DEBUG_MODE_ENABLED:
                print(f"{Fore.YELLOW}[WARNING] ListAvailableModels response is not JSON{Style.RESET_ALL}")
        except Exception as e:
            if DEBUG_MODE_ENABLED:
                print(f"{Fore.RED}[ERROR] Failed to inject models: {e}{Style.RESET_ALL}")
                import traceback
                traceback.print_exc()
    
    if 'amazonaws.com' in flow.request.pretty_host or 'kiro.dev' in flow.request.pretty_host:
        if DEBUG_MODE_ENABLED:
            print(f"\n{Fore.GREEN}{'='*60}")
            print(f"{Style.BRIGHT} [AWS RESPONSE]{Style.RESET_ALL}")
            print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Status:{Style.RESET_ALL} {Fore.GREEN}{flow.response.status_code}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}URL:{Style.RESET_ALL} {Style.DIM}{flow.request.pretty_url}{Style.RESET_ALL}")
            
            # Print response headers
            print(f"\n{Fore.YELLOW}Response Headers:{Style.RESET_ALL}")
            for k, v in flow.response.headers.items():
                if k.lower() in ['content-type', 'content-encoding', 'content-length', 'x-amzn-requestid']:
                    print(f"  {Fore.CYAN}{k}:{Style.RESET_ALL} {Style.DIM}{v}{Style.RESET_ALL}")

        if flow.response.content:
            if DEBUG_MODE_ENABLED:
                print(f"\n{Fore.YELLOW}Response Body ({len(flow.response.content)} bytes):{Style.RESET_ALL}")
            
            # Try multiple decoding strategies
            decoded = False
            
            # Strategy 1: Try as text/JSON
            try:
                text = flow.response.text
                # Try to parse as JSON
                try:
                    response_json = json.loads(text)
                    if DEBUG_MODE_ENABLED:
                        response_str = json.dumps(response_json, indent=2)
                        if len(response_str) > 1000:
                            print(f"  {Fore.GREEN}[JSON]{Style.RESET_ALL} {Style.DIM}{response_str[:1000]}...{Style.RESET_ALL}")
                        else:
                            print(f"  {Fore.GREEN}[JSON]{Style.RESET_ALL} {Style.DIM}{response_str}{Style.RESET_ALL}")
                    decoded = True
                    
                    # Save to file
                    if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                        filename = RESPONSES_DIR / f'response_{len(self.aws_requests)}.json'
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump({
                                'type': 'response',
                                'url': flow.request.pretty_url,
                                'status': flow.response.status_code,
                                'headers': dict(flow.response.headers),
                                'body': response_json
                            }, f, indent=2)
                except:
                    # Not JSON, but is text
                    if DEBUG_MODE_ENABLED:
                        if len(text) > 500:
                            print(f"  {Fore.CYAN}[TEXT]{Style.RESET_ALL} {Style.DIM}{text[:500]}...{Style.RESET_ALL}")
                        else:
                            print(f"  {Fore.CYAN}[TEXT]{Style.RESET_ALL} {Style.DIM}{text}{Style.RESET_ALL}")
                    decoded = True
                    
                    # Save raw text
                    if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                        filename = RESPONSES_DIR / f'response_{len(self.aws_requests)}.txt'
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(text)
            except Exception as e:
                pass
            
            # Strategy 2: Check if it's event-stream (streaming response)
            if not decoded and 'text/event-stream' in flow.response.headers.get('content-type', ''):
                try:
                    text = flow.response.content.decode('utf-8')
                    if DEBUG_MODE_ENABLED:
                        print(f"  {Fore.MAGENTA}[EVENT-STREAM]{Style.RESET_ALL}")
                        lines = text.split('\n')[:20]  # First 20 lines
                        for line in lines:
                            print(f"    {Style.DIM}{line}{Style.RESET_ALL}")
                        if len(text.split('\n')) > 20:
                            print(f"    {Style.DIM}... ({len(text.split('\n'))} total lines){Style.RESET_ALL}")
                    decoded = True
                    
                    # Save event-stream to file
                    if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                        filename = RESPONSES_DIR / f'response_{len(self.aws_requests)}_stream.txt'
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(text)
                except:
                    pass
            
            # Strategy 3: Binary/unknown
            if not decoded:
                if DEBUG_MODE_ENABLED:
                    print(f"  {Fore.YELLOW}[BINARY]{Style.RESET_ALL} First 100 bytes (hex):")
                    hex_data = flow.response.content[:100].hex()
                    print(f"    {Style.DIM}{hex_data}{Style.RESET_ALL}")
                
                # Try to identify format
                if flow.response.content[:2] == b'\x1f\x8b':
                    if DEBUG_MODE_ENABLED:
                        print(f"  {Fore.CYAN}Format:{Style.RESET_ALL} GZIP compressed")
                    try:
                        import gzip
                        decompressed = gzip.decompress(flow.response.content)
                        if DEBUG_MODE_ENABLED:
                            print(f"  {Fore.CYAN}Decompressed ({len(decompressed)} bytes):{Style.RESET_ALL}")
                            decompressed_text = decompressed[:500].decode('utf-8', errors='ignore')
                            print(f"    {Style.DIM}{decompressed_text}{Style.RESET_ALL}")
                        
                        # Save decompressed to file
                        if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                            filename = RESPONSES_DIR / f'response_{len(self.aws_requests)}_gzip.txt'
                            with open(filename, 'w', encoding='utf-8') as f:
                                f.write(decompressed.decode('utf-8', errors='ignore'))
                    except Exception as e:
                        if DEBUG_MODE_ENABLED:
                            print(f"  {Fore.RED}Failed to decompress: {e}{Style.RESET_ALL}")
                
                # Save binary to file
                if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                    filename = RESPONSES_DIR / f'response_{len(self.aws_requests)}.bin'
                    with open(filename, 'wb') as f:
                        f.write(flow.response.content)
                    if DEBUG_MODE_ENABLED:
                        print(f"  {Fore.GREEN}Saved binary to:{Style.RESET_ALL} {filename.name}")
        
        if DEBUG_MODE_ENABLED:
            print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}\n")
