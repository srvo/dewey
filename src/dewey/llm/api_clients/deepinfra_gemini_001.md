### OpenAI with python client

You can use the official openai python client to run inferences with us

    # Assume openai>=1.0.0
    from openai import OpenAI
    
    # Create an OpenAI client with your deepinfra token and endpoint
    openai = OpenAI(
        api_key="9BN9c7pQTDHy1EoKuNv53qe5ngfVlMVM",
        base_url="https://api.deepinfra.com/v1/openai",
    )
    
    chat_completion = openai.chat.completions.create(
        model="google/gemini-2.0-flash-001",
        messages=[{"role": "user", "content": "Hello"}],
    )
    
    print(chat_completion.choices[0].message.content)
    print(chat_completion.usage.prompt_tokens, chat_completion.usage.completion_tokens)
    
    # Hello! It's nice to meet you. Is there something I can help you with, or would you like to chat?
    # 11 25
    

#### Conversations

To create a longer chat-like conversation you just have to add each response message and each of the user messages to every request. This way the model will have the context and will be able to provide better answers. You can tweak it even further by providing a system message.

    # Assume openai>=1.0.0
    from openai import OpenAI
    
    # Create an OpenAI client with your deepinfra token and endpoint
    openai = OpenAI(
        api_key="9BN9c7pQTDHy1EoKuNv53qe5ngfVlMVM",
        base_url="https://api.deepinfra.com/v1/openai",
    )
    
    chat_completion = openai.chat.completions.create(
        model="google/gemini-2.0-flash-001",
        messages=[
            {"role": "system", "content": "Respond like a michelin starred chef."},
            {"role": "user", "content": "Can you name at least two different techniques to cook lamb?"},
            {"role": "assistant", "content": "Bonjour! Let me tell you, my friend, cooking lamb is an art form, and I'm more than happy to share with you not two, but three of my favorite techniques to coax out the rich, unctuous flavors and tender textures of this majestic protein. First, we have the classic \"Sous Vide\" method. Next, we have the ancient art of \"Sous le Sable\". And finally, we have the more modern technique of \"Hot Smoking.\""},
            {"role": "user", "content": "Tell me more about the second method."},
        ],
    )
    
    print(chat_completion.choices[0].message.content)
    print(chat_completion.usage.prompt_tokens, chat_completion.usage.completion_tokens)
    
    # Sous le Sable! It's an ancient technique that never goes out of style, n'est-ce pas? Literally ...
    # 149 324
    

The longer the conversation gets, the more time it takes the model to generate the response. The number of messages that you can have in a conversation is limited by the context size of a model. Larger models also usually take more time to respond.

  

### Streaming

Streaming any of the chat completions above is supported by adding the `stream=True` option.

    from openai import OpenAI
    
    # Create an OpenAI client with your deepinfra token and endpoint
    openai = OpenAI(
        api_key="9BN9c7pQTDHy1EoKuNv53qe5ngfVlMVM",
        base_url="https://api.deepinfra.com/v1/openai",
    )
    
    chat_completion = openai.chat.completions.create(
        model="google/gemini-2.0-flash-001",
        messages=[{"role": "user", "content": "Hello"}],
        stream=True,
    )
    
    for event in chat_completion:
        if event.choices[0].finish_reason:
            print(event.choices[0].finish_reason, event.usage["prompt_tokens"], event.usage["completion_tokens"])
        else:
            print(event.choices[0].delta.content)
    
    # Hello
    # !
    # It
    # 's
    # nice
    # ...
    # 11 25
    

## Input fields

[

### `model`_string_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-model)

model name

* * *

[

### `messages`_array_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-messages)

conversation messages: (user,assistant,tool)\*,user including one system message anywhere

* * *

[

### `stream`_boolean_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-stream)

whether to stream the output via SSE or return the full response

Default value: `false`

* * *

[

### `temperature`_number_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-temperature)

What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic

Default value: `1`

Range: `0 ≤ temperature ≤ 2`

* * *

[

### `top_p`_number_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-top_p)

An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top\_p probability mass. So 0.1 means only the tokens comprising the top 10% probability mass are considered.

Default value: `1`

Range: `0 < top_p ≤ 1`

* * *

[

### `min_p`_number_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-min_p)

Float that represents the minimum probability for a token to be considered, relative to the probability of the most likely token. Must be in \[0, 1\]. Set to 0 to disable this.

Default value: `0`

Range: `0 ≤ min_p ≤ 1`

* * *

[

### `top_k`_integer_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-top_k)

Sample from the best k (number of) tokens. 0 means off

Default value: `0`

Range: `0 ≤ top_k < 1000`

* * *

[

### `max_tokens`_integer_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-max_tokens)

The maximum number of tokens to generate in the chat completion. The total length of input tokens and generated tokens is limited by the model's context length. If explicitly set to None it will be the model's max context length minus input length or 8192, whichever is smaller.

Range: `0 ≤ max_tokens ≤ 1000000`

* * *

[

### `stop`_string_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-stop)

up to 16 sequences where the API will stop generating further tokens

* * *

[

### `n`_integer_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-n)

number of sequences to return

Default value: `1`

Range: `1 ≤ n ≤ 4`

* * *

[

### `presence_penalty`_number_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-presence_penalty)

Positive values penalize new tokens based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics.

Default value: `0`

Range: `-2 ≤ presence_penalty ≤ 2`

* * *

[

### `frequency_penalty`_number_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-frequency_penalty)

Positive values penalize new tokens based on how many times they appear in the text so far, increasing the model's likelihood to talk about new topics.

Default value: `0`

Range: `-2 ≤ frequency_penalty ≤ 2`

* * *

[

### `tools`_array_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-tools)

A list of tools the model may call. Currently, only functions are supported as a tool.

* * *

[

### `tool_choice`_string_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-tool_choice)

Controls which (if any) function is called by the model. none means the model will not call a function and instead generates a message. auto means the model can pick between generating a message or calling a function. specifying a particular function choice is not supported currently.none is the default when no functions are present. auto is the default if functions are present.

* * *

[

### `response_format`_object_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-response_format)

The format of the response. Currently, only json is supported.

* * *

[

### `repetition_penalty`_number_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-repetition_penalty)

Alternative penalty for repetition, but multiplicative instead of additive (> 1 penalize, < 1 encourage)

Default value: `1`

Range: `0.01 ≤ repetition_penalty ≤ 5`

* * *

[

### `user`_string_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-user)

A unique identifier representing your end-user, which can help monitor and detect abuse. Avoid sending us any identifying information. We recommend hashing user identifiers.

* * *

[

### `seed`_integer_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-seed)

Seed for random number generator. If not provided, a random seed is used. Determinism is not guaranteed.

Range: `-9223372036854776000 ≤ seed < 18446744073709552000`

* * *

[

### `logprobs`_boolean_

](https://deepinfra.com/google/gemini-2.0-flash-001/api?example=openai-python#input-logprobs)

Whether to return log probabilities of the output tokens or not.If true, returns the log probabilities of each output token returned in the \`content\` of \`message\`.

## Input Schema

This is the detailed description of the input parameters in JSON Schema format

    {
        "title": "OpenAIChatCompletionsIn",
        "type": "object",
        "properties": {
            "model": {
                "title": "Model",
                "description": "model name",
                "example": "meta-llama/Llama-2-70b-chat-hf",
                "type": "string"
            },
            "messages": {
                "title": "Messages",
                "description": "conversation messages: (user,assistant,tool)*,user including one system message anywhere",
                "type": "array",
                "items": {
                    "anyOf": [
                        {
                            "$ref": "#/definitions/ChatCompletionToolMessage"
                        },
                        {
                            "$ref": "#/definitions/ChatCompletionAssistantMessage"
                        },
                        {
                            "$ref": "#/definitions/ChatCompletionUserMessage"
                        },
                        {
                            "$ref": "#/definitions/ChatCompletionSystemMessage"
                        }
                    ]
                }
            },
            "stream": {
                "title": "Stream",
                "description": "whether to stream the output via SSE or return the full response",
                "default": false,
                "type": "boolean"
            },
            "temperature": {
                "title": "Temperature",
                "description": "What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic",
                "default": 1,
                "minimum": 0,
                "maximum": 2,
                "type": "number"
            },
            "top_p": {
                "title": "Top P",
                "description": "An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass. So 0.1 means only the tokens comprising the top 10% probability mass are considered.",
                "default": 1,
                "exclusiveMinimum": 0,
                "maximum": 1,
                "type": "number"
            },
            "min_p": {
                "title": "Min P",
                "description": "Float that represents the minimum probability for a token to be considered, relative to the probability of the most likely token. Must be in [0, 1]. Set to 0 to disable this.",
                "default": 0,
                "minimum": 0,
                "maximum": 1,
                "type": "number"
            },
            "top_k": {
                "title": "Top K",
                "description": "Sample from the best k (number of) tokens. 0 means off",
                "default": 0,
                "exclusiveMaximum": 1000,
                "minimum": 0,
                "type": "integer"
            },
            "max_tokens": {
                "title": "Max Tokens",
                "description": "The maximum number of tokens to generate in the chat completion.\n\nThe total length of input tokens and generated tokens is limited by the model's context length. If explicitly set to None it will be the model's max context length minus input length or 8192, whichever is smaller.",
                "minimum": 0,
                "maximum": 1000000,
                "type": "integer"
            },
            "stop": {
                "title": "Stop",
                "description": "up to 16 sequences where the API will stop generating further tokens",
                "anyOf": [
                    {
                        "type": "string"
                    },
                    {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                ]
            },
            "n": {
                "title": "N",
                "description": "number of sequences to return",
                "default": 1,
                "minimum": 1,
                "maximum": 4,
                "type": "integer"
            },
            "presence_penalty": {
                "title": "Presence Penalty",
                "description": "Positive values penalize new tokens based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics.",
                "default": 0,
                "minimum": -2,
                "maximum": 2,
                "type": "number"
            },
            "frequency_penalty": {
                "title": "Frequency Penalty",
                "description": "Positive values penalize new tokens based on how many times they appear in the text so far, increasing the model's likelihood to talk about new topics.",
                "default": 0,
                "minimum": -2,
                "maximum": 2,
                "type": "number"
            },
            "tools": {
                "title": "Tools",
                "description": "A list of tools the model may call. Currently, only functions are supported as a tool.",
                "type": "array",
                "items": {
                    "$ref": "#/definitions/ChatTools"
                }
            },
            "tool_choice": {
                "title": "Tool Choice",
                "description": "Controls which (if any) function is called by the model. none means the model will not call a function and instead generates a message. auto means the model can pick between generating a message or calling a function. specifying a particular function choice is not supported currently.none is the default when no functions are present. auto is the default if functions are present.",
                "type": "string"
            },
            "response_format": {
                "title": "Response Format",
                "description": "The format of the response. Currently, only json is supported.",
                "allOf": [
                    {
                        "$ref": "#/definitions/ResponseFormat"
                    }
                ]
            },
            "repetition_penalty": {
                "title": "Repetition Penalty",
                "description": "Alternative penalty for repetition, but multiplicative instead of additive (> 1 penalize, < 1 encourage)",
                "default": 1,
                "minimum": 0.01,
                "maximum": 5,
                "type": "number"
            },
            "user": {
                "title": "User",
                "description": "A unique identifier representing your end-user, which can help monitor and detect abuse. Avoid sending us any identifying information. We recommend hashing user identifiers.",
                "type": "string"
            },
            "seed": {
                "title": "Seed",
                "description": "Seed for random number generator. If not provided, a random seed is used. Determinism is not guaranteed.",
                "exclusiveMaximum": 18446744073709552000,
                "minimum": -9223372036854776000,
                "type": "integer"
            },
            "logprobs": {
                "title": "Logprobs",
                "description": "Whether to return log probabilities of the output tokens or not.If true, returns the log probabilities of each output token returned in the `content` of `message`.",
                "type": "boolean"
            }
        },
        "required": [
            "model",
            "messages"
        ],
        "definitions": {
            "ChatCompletionToolMessage": {
                "title": "ChatCompletionToolMessage",
                "type": "object",
                "properties": {
                    "role": {
                        "title": "Role",
                        "description": "the role of the author of this message",
                        "default": "tool",
                        "enum": [
                            "tool"
                        ],
                        "type": "string"
                    },
                    "content": {
                        "title": "Content",
                        "description": "the message content",
                        "type": "string"
                    },
                    "tool_call_id": {
                        "title": "Tool Call Id",
                        "type": "string"
                    }
                },
                "required": [
                    "content",
                    "tool_call_id"
                ]
            },
            "Function": {
                "title": "Function",
                "type": "object",
                "properties": {
                    "name": {
                        "title": "Name",
                        "description": "the name of the function to call",
                        "type": "string"
                    },
                    "arguments": {
                        "title": "Arguments",
                        "description": "the function arguments, generated by the model in JSON format. the model does not always generate valid JSON, and may hallucinate parameters not defined by your function schema",
                        "type": "string"
                    }
                },
                "required": [
                    "name",
                    "arguments"
                ]
            },
            "ChatCompletionMessageToolCall": {
                "title": "ChatCompletionMessageToolCall",
                "type": "object",
                "properties": {
                    "id": {
                        "title": "Id",
                        "description": "the id of the tool call",
                        "type": "string"
                    },
                    "type": {
                        "title": "Type",
                        "description": "the type of the tool call. only function is supported currently",
                        "type": "string"
                    },
                    "function": {
                        "title": "Function",
                        "description": "the function that the model called",
                        "allOf": [
                            {
                                "$ref": "#/definitions/Function"
                            }
                        ]
                    }
                },
                "required": [
                    "id",
                    "type",
                    "function"
                ]
            },
            "ChatCompletionAssistantMessage": {
                "title": "ChatCompletionAssistantMessage",
                "type": "object",
                "properties": {
                    "role": {
                        "title": "Role",
                        "description": "the role of the author of this message",
                        "default": "assistant",
                        "enum": [
                            "assistant"
                        ],
                        "type": "string"
                    },
                    "content": {
                        "title": "Content",
                        "description": "the message content",
                        "type": "string"
                    },
                    "name": {
                        "title": "Name",
                        "type": "string"
                    },
                    "tool_calls": {
                        "title": "Tool Calls",
                        "description": "the tool calls generated by the mode",
                        "type": "array",
                        "items": {
                            "$ref": "#/definitions/ChatCompletionMessageToolCall"
                        }
                    }
                }
            },
            "ChatCompletionContentPartText": {
                "title": "ChatCompletionContentPartText",
                "type": "object",
                "properties": {
                    "type": {
                        "title": "Type",
                        "enum": [
                            "text"
                        ],
                        "type": "string"
                    },
                    "text": {
                        "title": "Text",
                        "type": "string"
                    }
                },
                "required": [
                    "type",
                    "text"
                ]
            },
            "ImageURL": {
                "title": "ImageURL",
                "type": "object",
                "properties": {
                    "url": {
                        "title": "Url",
                        "type": "string"
                    },
                    "detail": {
                        "title": "Detail",
                        "default": "auto",
                        "enum": [
                            "auto",
                            "low",
                            "high"
                        ],
                        "type": "string"
                    }
                },
                "required": [
                    "url"
                ]
            },
            "ChatCompletionContentPartImage": {
                "title": "ChatCompletionContentPartImage",
                "type": "object",
                "properties": {
                    "type": {
                        "title": "Type",
                        "enum": [
                            "image_url"
                        ],
                        "type": "string"
                    },
                    "image_url": {
                        "$ref": "#/definitions/ImageURL"
                    }
                },
                "required": [
                    "type",
                    "image_url"
                ]
            },
            "InputAudio": {
                "title": "InputAudio",
                "type": "object",
                "properties": {
                    "data": {
                        "title": "Data",
                        "type": "string"
                    },
                    "format": {
                        "title": "Format",
                        "default": "wav",
                        "enum": [
                            "wav",
                            "mp3"
                        ],
                        "type": "string"
                    }
                },
                "required": [
                    "data"
                ]
            },
            "ChatCompletionContentPartAudio": {
                "title": "ChatCompletionContentPartAudio",
                "type": "object",
                "properties": {
                    "type": {
                        "title": "Type",
                        "enum": [
                            "input_audio"
                        ],
                        "type": "string"
                    },
                    "input_audio": {
                        "$ref": "#/definitions/InputAudio"
                    }
                },
                "required": [
                    "type",
                    "input_audio"
                ]
            },
            "ChatCompletionUserMessage": {
                "title": "ChatCompletionUserMessage",
                "type": "object",
                "properties": {
                    "role": {
                        "title": "Role",
                        "description": "the role of the author of this message",
                        "default": "user",
                        "enum": [
                            "user"
                        ],
                        "type": "string"
                    },
                    "content": {
                        "title": "Content",
                        "description": "the message content",
                        "anyOf": [
                            {
                                "type": "string"
                            },
                            {
                                "type": "array",
                                "items": {
                                    "anyOf": [
                                        {
                                            "$ref": "#/definitions/ChatCompletionContentPartText"
                                        },
                                        {
                                            "$ref": "#/definitions/ChatCompletionContentPartImage"
                                        },
                                        {
                                            "$ref": "#/definitions/ChatCompletionContentPartAudio"
                                        }
                                    ]
                                }
                            }
                        ]
                    },
                    "name": {
                        "title": "Name",
                        "type": "string"
                    }
                },
                "required": [
                    "content"
                ]
            },
            "ChatCompletionSystemMessage": {
                "title": "ChatCompletionSystemMessage",
                "type": "object",
                "properties": {
                    "role": {
                        "title": "Role",
                        "description": "the role of the author of this message",
                        "default": "system",
                        "enum": [
                            "system"
                        ],
                        "type": "string"
                    },
                    "content": {
                        "title": "Content",
                        "description": "the message content",
                        "type": "string"
                    },
                    "name": {
                        "title": "Name",
                        "type": "string"
                    }
                },
                "required": [
                    "content"
                ]
            },
            "FunctionDefinition": {
                "title": "FunctionDefinition",
                "type": "object",
                "properties": {
                    "name": {
                        "title": "Name",
                        "type": "string"
                    },
                    "description": {
                        "title": "Description",
                        "type": "string"
                    },
                    "parameters": {
                        "title": "Parameters",
                        "type": "object"
                    }
                },
                "required": [
                    "name"
                ]
            },
            "ChatTools": {
                "title": "ChatTools",
                "type": "object",
                "properties": {
                    "type": {
                        "title": "Type",
                        "default": "function",
                        "type": "string"
                    },
                    "function": {
                        "$ref": "#/definitions/FunctionDefinition"
                    }
                },
                "required": [
                    "function"
                ]
            },
            "ResponseFormat": {
                "title": "ResponseFormat",
                "type": "object",
                "properties": {
                    "type": {
                        "title": "Type",
                        "description": "Response type, such as JSON mode",
                        "default": "text",
                        "example": "json_object",
                        "enum": [
                            "text",
                            "json_object"
                        ],
                        "type": "string"
                    }
                }
            }
        }
    }

## Output Schema

This is the detailed description of the output parameters in JSON Schema format

    {
        "title": "OpenAIChatCompletionOut",
        "type": "object",
        "properties": {
            "id": {
                "title": "Id",
                "description": "a unique identifier for the completion",
                "type": "string"
            },
            "object": {
                "title": "Object",
                "description": "the object type, which is always chat.completion",
                "default": "chat.completion",
                "type": "string"
            },
            "created": {
                "title": "Created",
                "description": "unix timestamp of the completion",
                "type": "integer"
            },
            "model": {
                "title": "Model",
                "description": "model name",
                "example": "meta-llama/Llama-2-70b-chat-hf",
                "type": "string"
            },
            "choices": {
                "title": "Choices",
                "description": "a list of chat completion choices, can be more than one",
                "type": "array",
                "items": {
                    "$ref": "#/definitions/OpenAIChatCompletionChoice"
                }
            },
            "usage": {
                "title": "Usage",
                "description": "usage data for the completion request",
                "allOf": [
                    {
                        "$ref": "#/definitions/UsageInfo"
                    }
                ]
            }
        },
        "required": [
            "model",
            "choices",
            "usage"
        ],
        "definitions": {
            "Function": {
                "title": "Function",
                "type": "object",
                "properties": {
                    "name": {
                        "title": "Name",
                        "description": "the name of the function to call",
                        "type": "string"
                    },
                    "arguments": {
                        "title": "Arguments",
                        "description": "the function arguments, generated by the model in JSON format. the model does not always generate valid JSON, and may hallucinate parameters not defined by your function schema",
                        "type": "string"
                    }
                },
                "required": [
                    "name",
                    "arguments"
                ]
            },
            "ChatCompletionMessageToolCall": {
                "title": "ChatCompletionMessageToolCall",
                "type": "object",
                "properties": {
                    "id": {
                        "title": "Id",
                        "description": "the id of the tool call",
                        "type": "string"
                    },
                    "type": {
                        "title": "Type",
                        "description": "the type of the tool call. only function is supported currently",
                        "type": "string"
                    },
                    "function": {
                        "title": "Function",
                        "description": "the function that the model called",
                        "allOf": [
                            {
                                "$ref": "#/definitions/Function"
                            }
                        ]
                    }
                },
                "required": [
                    "id",
                    "type",
                    "function"
                ]
            },
            "ChatCompletionAssistantMessage": {
                "title": "ChatCompletionAssistantMessage",
                "type": "object",
                "properties": {
                    "role": {
                        "title": "Role",
                        "description": "the role of the author of this message",
                        "default": "assistant",
                        "enum": [
                            "assistant"
                        ],
                        "type": "string"
                    },
                    "content": {
                        "title": "Content",
                        "description": "the message content",
                        "type": "string"
                    },
                    "name": {
                        "title": "Name",
                        "type": "string"
                    },
                    "tool_calls": {
                        "title": "Tool Calls",
                        "description": "the tool calls generated by the mode",
                        "type": "array",
                        "items": {
                            "$ref": "#/definitions/ChatCompletionMessageToolCall"
                        }
                    }
                }
            },
            "FinishReason": {
                "title": "FinishReason",
                "description": "An enumeration.",
                "enum": [
                    "stop",
                    "length",
                    "tool_calls"
                ],
                "type": "string"
            },
            "OpenAIChatCompletionTokenLogprob": {
                "title": "OpenAIChatCompletionTokenLogprob",
                "type": "object",
                "properties": {
                    "token": {
                        "title": "Token",
                        "description": "The token.",
                        "type": "string"
                    },
                    "bytes": {
                        "title": "Bytes",
                        "description": "A list of integers representing the UTF-8 bytes representation of the token.",
                        "type": "array",
                        "items": {
                            "type": "integer"
                        }
                    },
                    "logprob": {
                        "title": "Logprob",
                        "description": "the log probability of the token",
                        "type": "number"
                    }
                },
                "required": [
                    "token",
                    "logprob"
                ]
            },
            "OpenAIChoiceLogProbs": {
                "title": "OpenAIChoiceLogProbs",
                "type": "object",
                "properties": {
                    "content": {
                        "title": "Content",
                        "description": "A list of message content tokens with log probability information.",
                        "type": "array",
                        "items": {
                            "$ref": "#/definitions/OpenAIChatCompletionTokenLogprob"
                        }
                    }
                }
            },
            "OpenAIChatCompletionChoice": {
                "title": "OpenAIChatCompletionChoice",
                "type": "object",
                "properties": {
                    "index": {
                        "title": "Index",
                        "description": "index of the choice in th list of choices",
                        "type": "integer"
                    },
                    "message": {
                        "title": "Message",
                        "description": "a chat completion message generated by the model",
                        "allOf": [
                            {
                                "$ref": "#/definitions/ChatCompletionAssistantMessage"
                            }
                        ]
                    },
                    "finish_reason": {
                        "description": "the reason the model stopped generating tokens. stop if the model hit a natural stop point or a provided stop sequence, length if the maximum number of tokens specified in the request was reached, tool_calls if the model called a tool.",
                        "allOf": [
                            {
                                "$ref": "#/definitions/FinishReason"
                            }
                        ]
                    },
                    "logprobs": {
                        "title": "Logprobs",
                        "description": "Log probability information for the choice.",
                        "allOf": [
                            {
                                "$ref": "#/definitions/OpenAIChoiceLogProbs"
                            }
                        ]
                    }
                },
                "required": [
                    "index",
                    "message"
                ]
            },
            "UsageInfo": {
                "title": "UsageInfo",
                "type": "object",
                "properties": {
                    "prompt_tokens": {
                        "title": "Prompt Tokens",
                        "description": "number of tokens in the prompt",
                        "default": 0,
                        "type": "integer"
                    },
                    "total_tokens": {
                        "title": "Total Tokens",
                        "description": "total number of tokens in the completion (prompt + completion)",
                        "default": 0,
                        "type": "integer"
                    },
                    "completion_tokens": {
                        "title": "Completion Tokens",
                        "description": "number of tokens generated in the completion",
                        "default": 0,
                        "type": "integer"
                    },
                    "estimated_cost": {
                        "title": "Estimated Cost",
                        "description": "estimated cost of the completion in USD",
                        "type": "number"
                    }
                }
            }
        }
    }

## Streaming Schema

This is the detailed description of the output stream parameters in JSON Schema format

    {
        "title": "OpenAIChatCompletionStreamOut",
        "type": "object",
        "properties": {
            "id": {
                "title": "Id",
                "description": "a unique identifier for the completion",
                "type": "string"
            },
            "object": {
                "title": "Object",
                "description": "the object type, which is always chat.completion.chunk",
                "default": "chat.completion.chunk",
                "type": "string"
            },
            "created": {
                "title": "Created",
                "description": "unix timestamp of the completion",
                "type": "integer"
            },
            "model": {
                "title": "Model",
                "description": "model name",
                "example": "meta-llama/Llama-2-70b-chat-hf",
                "type": "string"
            },
            "choices": {
                "title": "Choices",
                "description": "a list of chat completion choices, can be more than one",
                "type": "array",
                "items": {
                    "$ref": "#/definitions/OpenAIChatCompletionStreamChoice"
                }
            },
            "usage": {
                "title": "Usage",
                "description": "usage data about request and response",
                "allOf": [
                    {
                        "$ref": "#/definitions/UsageInfo"
                    }
                ]
            }
        },
        "required": [
            "model",
            "choices"
        ],
        "definitions": {
            "ChatMessageRole": {
                "title": "ChatMessageRole",
                "description": "An enumeration.",
                "enum": [
                    "system",
                    "user",
                    "assistant",
                    "tool"
                ],
                "type": "string"
            },
            "OpenAIDeltaToolCallFunction": {
                "title": "OpenAIDeltaToolCallFunction",
                "type": "object",
                "properties": {
                    "arguments": {
                        "title": "Arguments",
                        "type": "string"
                    },
                    "name": {
                        "title": "Name",
                        "type": "string"
                    }
                }
            },
            "OpenAIDeltaToolCall": {
                "title": "OpenAIDeltaToolCall",
                "type": "object",
                "properties": {
                    "index": {
                        "title": "Index",
                        "type": "integer"
                    },
                    "id": {
                        "title": "Id",
                        "type": "string"
                    },
                    "function": {
                        "$ref": "#/definitions/OpenAIDeltaToolCallFunction"
                    },
                    "type": {
                        "title": "Type",
                        "enum": [
                            "function"
                        ],
                        "type": "string"
                    }
                },
                "required": [
                    "index"
                ]
            },
            "OpenAIDeltaMessage": {
                "title": "OpenAIDeltaMessage",
                "type": "object",
                "properties": {
                    "role": {
                        "description": "the role of the author of this message",
                        "allOf": [
                            {
                                "$ref": "#/definitions/ChatMessageRole"
                            }
                        ]
                    },
                    "content": {
                        "title": "Content",
                        "description": "the chunk message content",
                        "type": "string"
                    },
                    "tool_calls": {
                        "title": "Tool Calls",
                        "description": "tool calls generated by the model",
                        "type": "array",
                        "items": {
                            "$ref": "#/definitions/OpenAIDeltaToolCall"
                        }
                    }
                }
            },
            "FinishReason": {
                "title": "FinishReason",
                "description": "An enumeration.",
                "enum": [
                    "stop",
                    "length",
                    "tool_calls"
                ],
                "type": "string"
            },
            "OpenAIChatCompletionStreamChoice": {
                "title": "OpenAIChatCompletionStreamChoice",
                "type": "object",
                "properties": {
                    "index": {
                        "title": "Index",
                        "description": "index of the choice in th list of choices",
                        "type": "integer"
                    },
                    "delta": {
                        "title": "Delta",
                        "description": "a chat completion delta generated by streamed model responses",
                        "allOf": [
                            {
                                "$ref": "#/definitions/OpenAIDeltaMessage"
                            }
                        ]
                    },
                    "finish_reason": {
                        "description": "the reason the model stopped generating tokens. stop if the model hit a natural stop point or a provided stop sequence, length if the maximum number of tokens specified in the request was reached, tool_calls if the model called a tool.",
                        "allOf": [
                            {
                                "$ref": "#/definitions/FinishReason"
                            }
                        ]
                    }
                },
                "required": [
                    "index",
                    "delta"
                ]
            },
            "UsageInfo": {
                "title": "UsageInfo",
                "type": "object",
                "properties": {
                    "prompt_tokens": {
                        "title": "Prompt Tokens",
                        "description": "number of tokens in the prompt",
                        "default": 0,
                        "type": "integer"
                    },
                    "total_tokens": {
                        "title": "Total Tokens",
                        "description": "total number of tokens in the completion (prompt + completion)",
                        "default": 0,
                        "type": "integer"
                    },
                    "completion_tokens": {
                        "title": "Completion Tokens",
                        "description": "number of tokens generated in the completion",
                        "default": 0,
                        "type": "integer"
                    },
                    "estimated_cost": {
                        "title": "Estimated Cost",
                        "description": "estimated cost of the completion in USD",
                        "type": "number"
                    }
                }
            }
        }
    }

