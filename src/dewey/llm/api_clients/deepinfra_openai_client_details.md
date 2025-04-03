# OpenAI API

We offer OpenAI compatible API for all [LLM models](https://deepinfra.com/models/text-generation) and all [Embeddings models](https://deepinfra.com/models/embeddings).

The APIs we support are:

-   [chat completion](https://platform.openai.com/docs/guides/gpt/chat-completions-api) — both streaming and regular
-   [completion](https://platform.openai.com/docs/guides/gpt/completions-api) — both streaming and regular
-   [embeddings](https://platform.openai.com/docs/guides/embeddings) — supported for all embeddings models.

The endpoint for the OpenAI APIs is `https://api.deepinfra.com/v1/openai`.

You can do HTTP requests. You can also use the official Python and Node.js libraries. In all cases streaming is also supported.

### Official libraries

For Python you should run

    pip install openai


For JavaScript/Node.js you should run

    npm install openai


### Chat Completions

The Chat Completions API is the easiest to use. You exchange messages and it just works. You can change the model to another LLM and it will continue working.

    from openai import OpenAI

    openai = OpenAI(
        api_key="$DEEPINFRA_TOKEN",
        base_url="https://api.deepinfra.com/v1/openai",
    )

    stream = True # or False

    chat_completion = openai.chat.completions.create(
        model="meta-llama/Meta-Llama-3-8B-Instruct",
        messages=[{"role": "user", "content": "Hello"}],
        stream=stream,
    )

    if stream:
        for event in chat_completion:
            if event.choices[0].finish_reason:
                print(event.choices[0].finish_reason,
                      event.usage['prompt_tokens'],
                      event.usage['completion_tokens'])
            else:
                print(event.choices[0].delta.content)
    else:
        print(chat_completion.choices[0].message.content)
        print(chat_completion.usage.prompt_tokens, chat_completion.usage.completion_tokens)


    import OpenAI from "openai";

    const openai = new OpenAI({
      apiKey: "$DEEPINFRA_TOKEN",
      baseURL: 'https://api.deepinfra.com/v1/openai',
    });

    const stream = false; // or true

    async function main() {
      const completion = await openai.chat.completions.create({
        messages: [{ role: "user", content: "Hello" }],
        model: "meta-llama/Meta-Llama-3-8B-Instruct",
        stream: stream,
      });

      if (stream) {
        for await (const chunk of completion) {
          if (chunk.choices[0].finish_reason) {
            console.log(chunk.choices[0].finish_reason,
                        chunk.usage.prompt_tokens,
                        chunk.usage.completion_tokens);
          } else {
            console.log(chunk.choices[0].delta.content);
          }
        }
      } else {
        console.log(completion.choices[0].message.content);
        console.log(completion.usage.prompt_tokens, completion.usage.completion_tokens);
      }
    }

    main();


    curl "https://api.deepinfra.com/v1/openai/chat/completions" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $DEEPINFRA_TOKEN" \
      -d '{
          "model": "meta-llama/Meta-Llama-3-8B-Instruct",
          "stream": true,
          "messages": [
            {
              "role": "user",
              "content": "Hello!"
            }
          ]
        }'


pythonjavascriptbash

You can see more complete examples at the documentation page of each model.

### Conversations with Chat Completions

To create a longer chat-like conversation you have to add each response message and each of the user's messages to every request. This way the model will have the context and will be able to provide better answers. You can tweak it even further by providing a system message.

    from openai import OpenAI

    openai = OpenAI(
        api_key="$DEEPINFRA_TOKEN",
        base_url="https://api.deepinfra.com/v1/openai",
    )

    stream = True # or False

    chat_completion = openai.chat.completions.create(
        model="meta-llama/Meta-Llama-3-8B-Instruct",
        messages=[
            {"role": "system", "content": "Respond like a michelin starred chef."},
            {"role": "user", "content": "Can you name at least two different techniques to cook lamb?"},
            {"role": "assistant", "content": "Bonjour! Let me tell you, my friend, cooking lamb is an art form, and I'm more than happy to share with you not two, but three of my favorite techniques to coax out the rich, unctuous flavors and tender textures of this majestic protein. First, we have the classic \"Sous Vide\" method. Next, we have the ancient art of \"Sous le Sable\". And finally, we have the more modern technique of \"Hot Smoking.\""},
            {"role": "user", "content": "Tell me more about the second method."},
        ],
        stream=stream,
    )

    if stream:
        for event in chat_completion:
            if event.choices[0].finish_reason:
                print(event.choices[0].finish_reason,
                      event.usage['prompt_tokens'],
                      event.usage['completion_tokens'])
            else:
                print(event.choices[0].delta.content)
    else:
        print(chat_completion.choices[0].message.content)
        print(chat_completion.usage.prompt_tokens, chat_completion.usage.completion_tokens)


    import OpenAI from "openai";

    const openai = new OpenAI({
      baseURL: 'https://api.deepinfra.com/v1/openai',
      apiKey: "$DEEPINFRA_TOKEN",
    });

    const stream = false; // or true

    async function main() {
      const completion = await openai.chat.completions.create({
        messages: [
          {role: "system", content: "Respond like a michelin starred chef."},
          {role: "user", content: "Can you name at least two different techniques to cook lamb?"},
          {role: "assistant", content: "Bonjour! Let me tell you, my friend, cooking lamb is an art form, and I'm more than happy to share with you not two, but three of my favorite techniques to coax out the rich, unctuous flavors and tender textures of this majestic protein. First, we have the classic \"Sous Vide\" method. Next, we have the ancient art of \"Sous le Sable\". And finally, we have the more modern technique of \"Hot Smoking.\""},
          {role: "user", "content": "Tell me more about the second method."}
        ],
        model: "meta-llama/Meta-Llama-3-8B-Instruct",
        stream: stream,
      });

      if (stream) {
        for await (const chunk of completion) {
          if (chunk.choices[0].finish_reason) {
            console.log(chunk.choices[0].finish_reason,
                        chunk.usage.prompt_tokens,
                        chunk.usage.completion_tokens);
          } else {
            console.log(chunk.choices[0].delta.content);
          }
        }
      } else {
        console.log(completion.choices[0].message.content);
        console.log(completion.usage.prompt_tokens, completion.usage.completion_tokens);
      }
    }

    main();


    curl "https://api.deepinfra.com/v1/openai/chat/completions" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $DEEPINFRA_TOKEN" \
      -d '{
          "model": "meta-llama/Meta-Llama-3-8B-Instruct",
          "stream": true,
          "messages": [
            {
                "role": "system",
                "content": "Respond like a michelin starred chef."
            },
            {
              "role": "user",
              "content": "Can you name at least two different techniques to cook lamb?"
            },
            {
              "role": "assistant",
              "content": "Bonjour! Let me tell you, my friend, cooking lamb is an art form, and I'"'"'m more than happy to share with you not two, but three of my favorite techniques to coax out the rich, unctuous flavors and tender textures of this majestic protein. First, we have the classic \"Sous Vide\" method. Next, we have the ancient art of \"Sous le Sable\". And finally, we have the more modern technique of \"Hot Smoking.\""
            },
            {
              "role": "user",
              "content": "Tell me more about the second method."
            }
          ]
        }'


pythonjavascriptbash

The longer the conversation gets, the more time it takes the model to generate the response. The number of messages that you can have in a conversation is limited by the context size of a model. Larger models also usually take more time to respond and are more expensive.

### Completions

This is an advanced API. You should know how to format the input to make it work. Different models might have a different input format. The example below is for [meta-llama/Meta-Llama-3-8B-Instruct](https://deepinfra.com/meta-llama/Meta-Llama-3-8B-Instruct). You can see the model's input format in the API section on its page.

    from openai import OpenAI

    openai = OpenAI(
        api_key="$DEEPINFRA_TOKEN",
        base_url="https://api.deepinfra.com/v1/openai",
    )

    stream = True # or False

    completion = openai.completions.create(
        model='meta-llama/Meta-Llama-3-8B-Instruct',
        prompt='<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\nHello!<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n',
        stop=['<|eot_id|>'],
        stream=stream,
    )

    if stream:
        for event in completion:
            if event.choices[0].finish_reason:
                print(event.choices[0].finish_reason,
                      event.usage.prompt_tokens,
                      event.usage.completion_tokens)
            else:
                print(event.choices[0].text)
    else:
        print(completion.choices[0].text)
        print(completion.usage.prompt_tokens, completion.usage.completion_tokens)


    import OpenAI from "openai";

    const openai = new OpenAI({
      baseURL: 'https://api.deepinfra.com/v1/openai',
      apiKey: "$DEEPINFRA_TOKEN",
    });

    stream = true // or false

    async function main() {
      const completion = await openai.completions.create({
        "model": "meta-llama/Meta-Llama-3-8B-Instruct",
        "prompt": "<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\nHello!<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
        "stream": stream,
        "stop": [
          "<|eot_id|>"
        ]
      });

      if (stream) {
        for await (const chunk of completion) {
          if (chunk.choices[0].finish_reason) {
              console.log(chunk.choices[0].finish_reason,
                          chunk.usage.prompt_tokens,
                          chunk.usage.completion_tokens);
          } else {
              console.log(chunk.choices[0].text);
          }
        }
      } else {
        console.log(completion.choices[0].text);
        console.log(completion.usage.prompt_tokens, completion.usage.completion_tokens);
      }
    }

    main();


    curl "https://api.deepinfra.com/v1/openai/completions" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $DEEPINFRA_TOKEN" \
      -d '{
         "model": "meta-llama/Meta-Llama-3-8B-Instruct",
         "prompt": "<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\nHello!<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
         "stop": [
           "<|eot_id|>"
         ]
       }'


pythonjavascriptbash

For every model you can check its input format in the API section on its page.

### Embeddings

DeepInfra supports the OpenAI embeddings API. The following creates an embedding vector representing the input text

    from openai import OpenAI

    openai = OpenAI(
        api_key="$DEEPINFRA_TOKEN",
        base_url="https://api.deepinfra.com/v1/openai",
    )

    input = "The food was delicious and the waiter...", # or an array ["hello", "world"]

    embeddings = openai.embeddings.create(
      model="BAAI/bge-large-en-v1.5",
      input=input,
      encoding_format="float"
    )

    if isinstance(input, str):
        print(embeddings.data[0].embedding)
    else:
        for i in range(len(input)):
            print(embeddings.data[i].embedding)

    print(embeddings.usage.prompt_tokens)


    import OpenAI from "openai";

    const openai = new OpenAI({
      baseURL: 'https://api.deepinfra.com/v1/openai',
      apiKey: "$DEEPINFRA_TOKEN",
    });

    const input = "The quick brown fox jumped over the lazy dog" // or an array ["hello", "world"]

    async function main() {
      const embedding = await openai.embeddings.create({
        model: "BAAI/bge-large-en-v1.5",
        input: input,
        encoding_format: "float",
      });

      // check if input is a string or array
      if (typeof input === "string") {
        console.log(embedding.data[0].embedding);
      } else {
        console.log(embedding.data.map((data) => data.embedding));
      }

      console.log(embedding.usage.prompt_tokens);
    }

    main();


    curl "https://api.deepinfra.com/v1/openai/embeddings" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $DEEPINFRA_TOKEN" \
      -d '{
        "input": "The food was delicious and the waiter...",
        "model": "BAAI/bge-large-en-v1.5",
        "encoding_format": "float"
      }'


pythonjavascriptbash

### Image Generation

You can use the OpenAI compatible API to generate images. Here's an example using Python:

    import io
    import base64
    from PIL import Image
    from openai import OpenAI

    client = OpenAI(
        api_key="$DEEPINFRA_TOKEN",
        base_url="https://api.deepinfra.com/v1/openai"
    )

    if __name__ == "__main__":
        response = client.images.generate(
            prompt="A photo of an astronaut riding a horse on Mars.",
            size="1024x1024",
            quality="standard",
            n=1,
        )
        b64_json = response.data[0].b64_json
        image_bytes = base64.b64decode(b64_json)
        image = Image.open(io.BytesIO(image_bytes))
        image.save("output.png")


    import * as fs from 'fs';
    import OpenAI from "openai";

    const openai = new OpenAI({
      baseURL: 'https://api.deepinfra.com/v1/openai',
      apiKey: "$DEEPINFRA_TOKEN",
    });

    async function main() {
      const response = await openai.images.generate({
        prompt: "A photo of an astronaut riding a horse on Mars.",
        size: "1024x1024",
        n: 1,
      });

      const b64Json = response.data[0].b64_json;
      const imageBuffer = Buffer.from(b64Json, 'base64');
      fs.writeFileSync('output.png', imageBuffer);
    }

    main();


    curl "https://api.deepinfra.com/v1/openai/images/generations" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $DEEPINFRA_TOKEN" \
      -d '{
        "prompt": "A photo of an astronaut riding a horse on Mars.",
        "size": "1024x1024",
        "n": 1
      }'


pythonjavascriptbash

## Model parameter

Some models have more than one version available, you can infer against a particular version by specifying `{"model": "MODEL_NAME:VERSION", ...}` format.

You could also infer against a `deploy_id`, by using `{"model": "deploy_id:DEPLOY_ID", ...}`. This is especially useful for [Custom LLMs](https://deepinfra.com/docs/advanced/custom_llms), you can infer before the deployment is running (and before you have the model-name+version pair).

## Caveats

Please note that we might not be 100% compatible yet, let us know in discord or by email if something you require is missing. Supported request attributes:

ChatCompletions and Completions:

-   `model`, including specifying `version`/`deploy_id` support
-   `messages` (roles `system`, `user`, `assistant`)
-   `max_tokens`
-   `stream`
-   `temperature`
-   `top_p`
-   `stop`
-   `n`
-   `presence_penalty`
-   `frequency_penalty`
-   `response_format` (`{"type": "json"}` only, it will return default format when omitted)
-   `tools`, `tool_choice`
-   `echo`, `logprobs` -- only for (non chat) completions

`deploy_id` might not be immediately avaiable if the model is currently deploying

Embeddings:

-   `model`
-   `input`
-   `encoding_format` -- `float` only

Images:

-   `model` -- Defaults to FLUX Schnell
-   `quality` and `style` -- only available for compatibility.
-   `response_format` -- only `b64_json` supported for now.

You can see even more details on each model's page.

[Inference](https://deepinfra.com/docs/inference)[DeepInfra API](https://deepinfra.com/docs/deep_infra_api)


### DEEPSEEK - R1 (use for thinking task)

You can use the official openai python client to run inferences with us

    # Assume openai>=1.0.0
    from openai import OpenAI

    # Create an OpenAI client with your deepinfra token and endpoint
    openai = OpenAI(
        api_key="o2xZwwhBW4JmF5k0cD1jjBFsjlS8iCcc",
        base_url="https://api.deepinfra.com/v1/openai",
    )

    chat_completion = openai.chat.completions.create(
        model="deepseek-ai/DeepSeek-R1",
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
        api_key="o2xZwwhBW4JmF5k0cD1jjBFsjlS8iCcc",
        base_url="https://api.deepinfra.com/v1/openai",
    )

    chat_completion = openai.chat.completions.create(
        model="deepseek-ai/DeepSeek-R1",
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
        api_key="o2xZwwhBW4JmF5k0cD1jjBFsjlS8iCcc",
        base_url="https://api.deepinfra.com/v1/openai",
    )

    chat_completion = openai.chat.completions.create(
        model="deepseek-ai/DeepSeek-R1",
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

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-model)

model name

* * *

[

### `messages`_array_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-messages)

conversation messages: (user,assistant,tool)\*,user including one system message anywhere

* * *

[

### `stream`_boolean_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-stream)

whether to stream the output via SSE or return the full response

Default value: `false`

* * *

[

### `temperature`_number_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-temperature)

What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic

Default value: `1`

Range: `0 ≤ temperature ≤ 2`

* * *

[

### `top_p`_number_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-top_p)

An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top\_p probability mass. So 0.1 means only the tokens comprising the top 10% probability mass are considered.

Default value: `1`

Range: `0 < top_p ≤ 1`

* * *

[

### `min_p`_number_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-min_p)

Float that represents the minimum probability for a token to be considered, relative to the probability of the most likely token. Must be in \[0, 1\]. Set to 0 to disable this.

Default value: `0`

Range: `0 ≤ min_p ≤ 1`

* * *

[

### `top_k`_integer_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-top_k)

Sample from the best k (number of) tokens. 0 means off

Default value: `0`

Range: `0 ≤ top_k < 1000`

* * *

[

### `max_tokens`_integer_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-max_tokens)

The maximum number of tokens to generate in the chat completion. The total length of input tokens and generated tokens is limited by the model's context length. If explicitly set to None it will be the model's max context length minus input length or 8192, whichever is smaller.

Range: `0 ≤ max_tokens ≤ 1000000`

* * *

[

### `stop`_string_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-stop)

up to 16 sequences where the API will stop generating further tokens

* * *

[

### `n`_integer_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-n)

number of sequences to return

Default value: `1`

Range: `1 ≤ n ≤ 4`

* * *

[

### `presence_penalty`_number_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-presence_penalty)

Positive values penalize new tokens based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics.

Default value: `0`

Range: `-2 ≤ presence_penalty ≤ 2`

* * *

[

### `frequency_penalty`_number_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-frequency_penalty)

Positive values penalize new tokens based on how many times they appear in the text so far, increasing the model's likelihood to talk about new topics.

Default value: `0`

Range: `-2 ≤ frequency_penalty ≤ 2`

* * *

[

### `tools`_array_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-tools)

A list of tools the model may call. Currently, only functions are supported as a tool.

* * *

[

### `tool_choice`_string_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-tool_choice)

Controls which (if any) function is called by the model. none means the model will not call a function and instead generates a message. auto means the model can pick between generating a message or calling a function. specifying a particular function choice is not supported currently.none is the default when no functions are present. auto is the default if functions are present.

* * *

[

### `response_format`_object_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-response_format)

The format of the response. Currently, only json is supported.

* * *

[

### `repetition_penalty`_number_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-repetition_penalty)

Alternative penalty for repetition, but multiplicative instead of additive (> 1 penalize, < 1 encourage)

Default value: `1`

Range: `0.01 ≤ repetition_penalty ≤ 5`

* * *

[

### `user`_string_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-user)

A unique identifier representing your end-user, which can help monitor and detect abuse. Avoid sending us any identifying information. We recommend hashing user identifiers.

* * *

[

### `seed`_integer_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-seed)

Seed for random number generator. If not provided, a random seed is used. Determinism is not guaranteed.

Range: `-9223372036854776000 ≤ seed < 18446744073709552000`

* * *

[

### `logprobs`_boolean_

](https://deepinfra.com/deepseek-ai/DeepSeek-R1/api?example=openai-python#input-logprobs)

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
