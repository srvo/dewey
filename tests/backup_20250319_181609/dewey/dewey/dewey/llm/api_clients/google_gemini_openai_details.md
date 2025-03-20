# Google gemini -- use for long context and free inference on non-sensitive info

# Long context

-   On this page
-   [What is a context window?](https://ai.google.dev/gemini-api/docs/long-context#what-is-context-window)
-   [Getting started with long context](https://ai.google.dev/gemini-api/docs/long-context#getting-started-with-long-context)
-   [Long context use cases](https://ai.google.dev/gemini-api/docs/long-context#long-context-use-cases)
    -   [Long form text](https://ai.google.dev/gemini-api/docs/long-context#long-form-text)
    -   [Long form video](https://ai.google.dev/gemini-api/docs/long-context#long-form-video)
    -   [Long form audio](https://ai.google.dev/gemini-api/docs/long-context#long-form-audio)
-   [Long context optimizations](https://ai.google.dev/gemini-api/docs/long-context#long-context-optimizations)
-   [Long context limitations](https://ai.google.dev/gemini-api/docs/long-context#long-context-limitations)
-   [FAQs](https://ai.google.dev/gemini-api/docs/long-context#faqs)
    -   [Do I lose model performance when I add more tokens to a query?](https://ai.google.dev/gemini-api/docs/long-context#do_i_lose_model_performance_when_i_add_more_tokens_to_a_query)
    -   [How does Gemini 1.5 Pro perform on the standard needle-in-a-haystack test?](https://ai.google.dev/gemini-api/docs/long-context#how_does_gemini_15_pro_perform_on_the_standard_needle-in-a-haystack_test)
    -   [How can I lower my cost with long-context queries?](https://ai.google.dev/gemini-api/docs/long-context#how_can_i_lower_my_cost_with_long-context_queries)
    -   [How can I get access to the 2-million-token context window?](https://ai.google.dev/gemini-api/docs/long-context#how_can_i_get_access_to_the_2-million-token_context_window)
    -   [Does the context length affect the model latency?](https://ai.google.dev/gemini-api/docs/long-context#does_the_context_length_affect_the_model_latency)
    -   [Do the long context capabilities differ between Gemini 1.5 Flash and Gemini 1.5 Pro?](https://ai.google.dev/gemini-api/docs/long-context#do_the_long_context_capabilities_differ_between_gemini_15_flash_and_gemini_15_pro)

Gemini 2.0 Flash and Gemini 1.5 Flash come with a 1-million-token context window, and Gemini 1.5 Pro comes with a 2-million-token context window. Historically, large language models (LLMs) were significantly limited by the amount of text (or tokens) that could be passed to the model at one time. The Gemini 1.5 long context window, with [near-perfect retrieval (>99%)](https://storage.googleapis.com/deepmind-media/gemini/gemini_v1_5_report.pdf), unlocks many new use cases and developer paradigms.

The code you already use for cases like [text generation](https://ai.google.dev/gemini-api/docs/text-generation) or [multimodal inputs](https://ai.google.dev/gemini-api/docs/vision) will work out of the box with long context.

Throughout this guide, you briefly explore the basics of the context window, how developers should think about long context, various real world use cases for long context, and ways to optimize the usage of long context.

## What is a context window?

The basic way you use the Gemini models is by passing information (context) to the model, which will subsequently generate a response. An analogy for the context window is short term memory. There is a limited amount of information that can be stored in someone's short term memory, and the same is true for generative models.

You can read more about how models work under the hood in our [generative models guide](https://ai.google.dev/gemini-api/docs/models/generative-models).

## Getting started with long context

Most generative models created in the last few years were only capable of processing 8,000 tokens at a time. Newer models pushed this further by accepting 32,000 tokens or 128,000 tokens. Gemini 1.5 is the first model capable of accepting 1 million tokens, and now [2 million tokens with Gemini 1.5 Pro](https://developers.googleblog.com/en/new-features-for-the-gemini-api-and-google-ai-studio/).

In practice, 1 million tokens would look like:

-   50,000 lines of code (with the standard 80 characters per line)
-   All the text messages you have sent in the last 5 years
-   8 average length English novels
-   Transcripts of over 200 average length podcast episodes

Even though the models can take in more and more context, much of the conventional wisdom about using large language models assumes this inherent limitation on the model, which as of 2024, is no longer the case.

Some common strategies to handle the limitation of small context windows included:

-   Arbitrarily dropping old messages / text from the context window as new text comes in
-   Summarizing previous content and replacing it with the summary when the context window gets close to being full
-   Using RAG with semantic search to move data out of the context window and into a vector database
-   Using deterministic or generative filters to remove certain text / characters from prompts to save tokens

While many of these are still relevant in certain cases, the default place to start is now just putting all of the tokens into the context window. Because Gemini models were purpose-built with a long context window, they are much more capable of in-context learning. For example, with only instructional materials (a 500-page reference grammar, a dictionary, and ≈ 400 extra parallel sentences) all provided in context, Gemini 1.5 Pro and Gemini 1.5 Flash are [capable of learning to translate](https://storage.googleapis.com/deepmind-media/gemini/gemini_v1_5_report.pdf) from English to Kalamang— a Papuan language with fewer than 200 speakers and therefore almost no online presence—with quality similar to a person who learned from the same materials.

This example underscores how you can start to think about what is possible with long context and the in-context learning capabilities of Gemini models.

## Long context use cases

While the standard use case for most generative models is still text input, the Gemini 1.5 model family enables a new paradigm of multimodal use cases. These models can natively understand text, video, audio, and images. They are accompanied by the [Gemini API that takes in multimodal file types](https://ai.google.dev/gemini-api/docs/prompting_with_media) for convenience.

### Long form text

Text has proved to be the layer of intelligence underpinning much of the momentum around LLMs. As mentioned earlier, much of the practical limitation of LLMs was because of not having a large enough context window to do certain tasks. This led to the rapid adoption of retrieval augmented generation (RAG) and other techniques which dynamically provide the model with relevant contextual information. Now, with larger and larger context windows (currently up to 2 million on Gemini 1.5 Pro), there are new techniques becoming available which unlock new use cases.

Some emerging and standard use cases for text based long context include:

-   Summarizing large corpuses of text
    -   Previous summarization options with smaller context models would require a sliding window or another technique to keep state of previous sections as new tokens are passed to the model
-   Question and answering
    -   Historically this was only possible with RAG given the limited amount of context and models' factual recall being low
-   Agentic workflows
    -   Text is the underpinning of how agents keep state of what they have done and what they need to do; not having enough information about the world and the agent's goal is a limitation on the reliability of agents

[Many-shot in-context learning](https://arxiv.org/pdf/2404.11018) is one of the most unique capabilities unlocked by long context models. Research has shown that taking the common "single shot" or "multi-shot" example paradigm, where the model is presented with one or a few examples of a task, and scaling that up to hundreds, thousands, or even hundreds of thousands of examples, can lead to novel model capabilities. This many-shot approach has also been shown to perform similarly to models which were fine-tuned for a specific task. For use cases where a Gemini model's performance is not yet sufficient for a production rollout, you can try the many-shot approach. As you might explore later in the long context optimization section, context caching makes this type of high input token workload much more economically feasible and even lower latency in some cases.

### Long form video

Video content's utility has long been constrained by the lack of accessibility of the medium itself. It was hard to skim the content, transcripts often failed to capture the nuance of a video, and most tools don't process image, text, and audio together. With Gemini 1.5, the long-context text capabilities translate to the ability to reason and answer questions about multimodal inputs with sustained performance. Gemini 1.5 Flash, when tested on the needle in a video haystack problem with 1M tokens, obtained >99.8% recall of the video in the context window, and 1.5 Pro reached state of the art performance on the [Video-MME benchmark](https://video-mme.github.io/home_page.html).

Some emerging and standard use cases for video long context include:

-   Video question and answering
-   Video memory, as shown with [Google's Project Astra](https://deepmind.google/technologies/gemini/project-astra/)
-   Video captioning
-   Video recommendation systems, by enriching existing metadata with new multimodal understanding
-   Video customization, by looking at a corpus of data and associated video metadata and then removing parts of videos that are not relevant to the viewer
-   Video content moderation
-   Real-time video processing

When working with videos, it is important to consider how the [videos are processed into tokens](https://ai.google.dev/gemini-api/docs/tokens#media-token), which affects billing and usage limits. You can learn more about prompting with video files in the [Prompting guide](https://ai.google.dev/gemini-api/docs/prompting_with_media?lang=python#prompting-with-videos).

### Long form audio

The Gemini 1.5 models were the first natively multimodal large language models that could understand audio. Historically, the typical developer workflow would involve stringing together multiple domain specific models, like a speech-to-text model and a text-to-text model, in order to process audio. This led to additional latency required by performing multiple round-trip requests and decreased performance usually attributed to disconnected architectures of the multiple model setup.

On standard audio-haystack evaluations, Gemini 1.5 Pro is able to find the hidden audio in 100% of the tests and Gemini 1.5 Flash is able to find it in 98.7% [of the tests](https://storage.googleapis.com/deepmind-media/gemini/gemini_v1_5_report.pdf). Gemini 1.5 Flash accepts up to 9.5 hours of [audio in a single request](https://ai.google.dev/gemini-api/docs/prompting_with_media?lang=python#audio_formats) and Gemini 1.5 Pro can accept up to 19 hours of audio using the 2-million-token context window. Further, on a test set of 15-minute audio clips, Gemini 1.5 Pro archives a word error rate (WER) of ~5.5%, much lower than even specialized speech-to-text models, without the added complexity of extra input segmentation and pre-processing.

Some emerging and standard use cases for audio context include:

-   Real-time transcription and translation
-   Podcast / video question and answering
-   Meeting transcription and summarization
-   Voice assistants

You can learn more about prompting with audio files in the [Prompting guide](https://ai.google.dev/gemini-api/docs/prompting_with_media?lang=python#prompting-with-videos).

## Long context optimizations

The primary optimization when working with long context and the Gemini 1.5 models is to use [context caching](https://ai.google.dev/gemini-api/docs/caching). Beyond the previous impossibility of processing lots of tokens in a single request, the other main constraint was the cost. If you have a "chat with your data" app where a user uploads 10 PDFs, a video, and some work documents, you would historically have to work with a more complex retrieval augmented generation (RAG) tool / framework in order to process these requests and pay a significant amount for tokens moved into the context window. Now, you can cache the files the user uploads and pay to store them on a per hour basis. The input / output cost per request with Gemini 1.5 Flash for example is ~4x less than the standard input / output cost, so if the user chats with their data enough, it becomes a huge cost saving for you as the developer.

## Long context limitations

In various sections of this guide, we talked about how Gemini 1.5 models achieve high performance across various needle-in-a-haystack retrieval evals. These tests consider the most basic setup, where you have a single needle you are looking for. In cases where you might have multiple "needles" or specific pieces of information you are looking for, the model does not perform with the same accuracy. Performance can vary to a wide degree depending on the context. This is important to consider as there is an inherent tradeoff between getting the right information retrieved and cost. You can get ~99% on a single query, but you have to pay the input token cost every time you send that query. So for 100 pieces of information to be retrieved, if you needed 99% performance, you would likely need to send 100 requests. This is a good example of where context caching can significantly reduce the cost associated with using Gemini models while keeping the performance high.

## FAQs

### Do I lose model performance when I add more tokens to a query?

Generally, if you don't need tokens to be passed to the model, it is best to avoid passing them. However, if you have a large chunk of tokens with some information and want to ask questions about that information, the model is highly capable of extracting that information (up to 99% accuracy in many cases).

### How does Gemini 1.5 Pro perform on the standard needle-in-a-haystack test?

Gemini 1.5 Pro achieves 100% recall up to 530k tokens and >99.7% recall [up to 1M tokens](https://storage.googleapis.com/deepmind-media/gemini/gemini_v1_5_report.pdf).

### How can I lower my cost with long-context queries?

If you have a similar set of tokens / context that you want to re-use many times, [context caching](https://ai.google.dev/gemini-api/docs/caching) can help reduce the costs associated with asking questions about that information.

### How can I get access to the 2-million-token context window?

All developers now have access to the 2-million-token context window with Gemini 1.5 Pro.

### Does the context length affect the model latency?

There is some fixed amount of latency in any given request, regardless of the size, but generally longer queries will have higher latency (time to first token).

### Do the long context capabilities differ between Gemini 1.5 Flash and Gemini 1.5 Pro?

Yes, some of the numbers were mentioned in different sections of this guide, but generally Gemini 1.5 Pro is more performant on most long context use cases.


# Code execution

-   On this page
-   [Get started with code execution](https://ai.google.dev/gemini-api/docs/code-execution?lang=python#get-started)
    -   [Enable code execution on the model](https://ai.google.dev/gemini-api/docs/code-execution?lang=python#enable-on-model)
    -   [Use code execution in chat](https://ai.google.dev/gemini-api/docs/code-execution?lang=python#code-in-chat)
-   [Input/output (I/O)](https://ai.google.dev/gemini-api/docs/code-execution?lang=python#input-output)
    -   [I/O pricing](https://ai.google.dev/gemini-api/docs/code-execution?lang=python#input-output-pricing)
    -   [I/O details](https://ai.google.dev/gemini-api/docs/code-execution?lang=python#input-output-details)
-   [Billing](https://ai.google.dev/gemini-api/docs/code-execution?lang=python#billing)
-   [Limitations](https://ai.google.dev/gemini-api/docs/code-execution?lang=python#limitations)

Python Node.js Go REST

The Gemini API code execution feature enables the model to generate and run Python code and learn iteratively from the results until it arrives at a final output. You can use this code execution capability to build applications that benefit from code-based reasoning and that produce text output. For example, you could use code execution in an application that solves equations or processes text.

Code execution is available in both AI Studio and the Gemini API. In AI Studio, you can enable code execution in the right panel under **Tools**. The Gemini API provides code execution as a tool, similar to [function calling](https://ai.google.dev/gemini-api/docs/function-calling/tutorial). After you add code execution as a tool, the model decides when to use it.

The code execution environment includes the following libraries: `altair`, `chess`, `cv2`, `matplotlib`, `mpmath`, `numpy`, `pandas`, `pdfminer`, `reportlab`, `seaborn`, `sklearn`, `statsmodels`, `striprtf`, `sympy`, and `tabulate`. You can't install your own libraries.

**Note:** Only `matplotlib` is supported for graph rendering using code execution.

## Get started with code execution

A code execution notebook is also available:

[![](https://ai.google.dev/static/site-assets/images/docs/notebook-site-button.png)View on ai.google.dev](https://ai.google.dev/gemini-api/docs/code-execution)

[![](https://www.tensorflow.org/images/colab_logo_32px.png)Try a Colab notebook](https://colab.research.google.com/github/google-gemini/cookbook/blob/main/quickstarts/Code_Execution.ipynb)

[![](https://www.tensorflow.org/images/GitHub-Mark-32px.png)View notebook on GitHub](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Code_Execution.ipynb)

This section assumes that you've completed the setup and configuration steps shown in the [quickstart](https://ai.google.dev/gemini-api/docs/quickstart).

### Enable code execution on the model

You can enable code execution on the model, as shown here:

from google import genai
    from google.genai import types
    
    client = genai.Client(api_key="GEMINI_API_KEY")
    
    response = client.models.generate_content(
      model='gemini-2.0-flash',
      contents='What is the sum of the first 50 prime numbers? '
               'Generate and run code for the calculation, and make sure you get all 50.',
      config=types.GenerateContentConfig(
        tools=[types.Tool(
          code_execution=types.ToolCodeExecution
        )]
      )
    )

In a notebook you can display everything in Markdown format with this helper function:

def display_code_execution_result(response):
      for part in response.candidates[0].content.parts:
        if part.text is not None:
          display(Markdown(part.text))
        if part.executable_code is not None:
          code_html = f'<pre style="background-color: #BBBBEE;">{part.executable_code.code}</pre>' # Change code color
          display(HTML(code_html))
        if part.code_execution_result is not None:
          display(Markdown(part.code_execution_result.output))
        if part.inline_data is not None:
          display(Image(data=part.inline_data.data, format="png"))
        display(Markdown("---"))
    
    display_code_execution_result(response)

The output might look something like this:

Okay, I need to calculate the sum of the first 50 prime numbers. I will use a python script to generate the first 50 primes and then sum them up.

\`\`\`python
def is\_prime(n):
  """Checks if a number is prime."""
  if n <= 1:
    return False
  for i in range(2, int(n\*\*0.5) + 1):
    if n % i == 0:
      return False
  return True

def sum\_of\_primes(n):
  """Calculates the sum of the first n prime numbers."""
  primes = \[\]
  i = 2
  while len(primes) < n:
    if is\_prime(i):
      primes.append(i)
    i += 1
  return sum(primes)

# Calculate the sum of the first 50 prime numbers
sum\_of\_first\_50\_primes = sum\_of\_primes(50)

print(f"The sum of the first 50 prime numbers is: {sum\_of\_first\_50\_primes}")
\`\`\`

\*\*Output:\*\*

\`\`\`
The sum of the first 50 prime numbers is: 5117
\`\`\`

### Use code execution in chat

You can also use code execution as part of a chat.

from google import genai
    from google.genai import types
    
    client = genai.Client(api_key="GEMINI_API_KEY")
    
    chat = client.chats.create(
        model='gemini-2.0-flash',
        config=types.GenerateContentConfig(
          tools=[types.Tool(
            code_execution=types.ToolCodeExecution
          )]
        )
    )
    
    response = chat.send_message("Can you run some code to bogo-sort this list of numbers?: [2,34,1,65,4]")
    display_code_execution_result(response)

The conversation could continue like this:

I understand that you want me to bogo-sort the list \[2, 34, 1, 65, 4\]. Bogo-sort is a notoriously inefficient sorting algorithm. It works by repeatedly shuffling the list until it happens to be sorted. Due to its extremely poor performance, it's impractical for lists of any significant size.

However, for demonstration purposes, I can run a simplified version for a very limited number of iterations, just to show the process. Should I go ahead?

response = chat.send_message("Yes, please create the code.")
    display_code_execution_result(response)

Okay,I will proceed with a function that shuffles the list and checks if it's sorted. I'll run it for a maximum of 10 iterations. ...

## Input/output (I/O)

Starting with [Gemini 2.0 Flash](https://ai.google.dev/gemini-api/docs/models/gemini#gemini-2.0-flash), code execution supports file input and graph output. Using these new input and output capabilities, you can upload CSV and text files, ask questions about the files, and have [Matplotlib](https://matplotlib.org/) graphs generated as part of the response.

### I/O pricing

When using code execution I/O, you're charged for input tokens and output tokens:

**Input tokens:**

-   User prompt

**Output tokens:**

-   Code generated by the model
-   Code execution output in the code environment
-   Summary generated by the model

### I/O details

When you're working with code execution I/O, be aware of the following technical details:

-   The maximum runtime of the code environment is 30 seconds.
-   If the code environment generates an error, the model may decide to regenerate the code output. This can happen up to 5 times.
-   The maximum file input size is limited by the model token window. In AI Studio, using Gemini Flash 2.0, the maximum input file size is 1 million tokens (roughly 2MB for text files of the supported input types). If you upload a file that's too large, AI Studio won't let you send it.

Single turn

Bidirectional (Multimodal Live API)

Models supported

All Gemini 2.0 models

Only Flash experimental models

File input types supported

.png, .jpeg, .csv, .xml, .cpp, .java, .py, .js, .ts

.png, .jpeg, .csv, .xml, .cpp, .java, .py, .js, .ts

Plotting libraries supported

Matplotlib

Matplotlib

[Multi-tool use](https://ai.google.dev/gemini-api/docs/function-calling#multi-tool-use)

No

Yes

## Billing

There's no additional charge for enabling code execution from the Gemini API. You'll be billed at the current rate of input and output tokens based on the Gemini model you're using.

Here are a few other things to know about billing for code execution:

-   You're only billed once for the input tokens you pass to the model, and you're billed for the final output tokens returned to you by the model.
-   Tokens representing generated code are counted as output tokens. Generated code can include text and multimodal output like images.
-   Code execution results are also counted as output tokens.

The billing model is shown in the following diagram:

![code execution billing model](https://ai.google.dev/static/gemini-api/docs/images/code-execution-diagram.png)

-   You're billed at the current rate of input and output tokens based on the Gemini model you're using.
-   If Gemini uses code execution when generating your response, the original prompt, the generated code, and the result of the executed code are labeled _intermediate tokens_ and are billed as _input tokens_.
-   Gemini then generates a summary and returns the generated code, the result of the executed code, and the final summary. These are billed as _output tokens_.
-   The Gemini API includes an intermediate token count in the API response, so you know why you're getting additional input tokens beyond your initial prompt.

## Limitations

-   The model can only generate and execute code. It can't return other artifacts like media files.
-   In some cases, enabling code execution can lead to regressions in other areas of model output (for example, writing a story).
-   There is some variation in the ability of the different models to use code execution successfully.

# Generate structured output with the Gemini API

-   On this page
-   [Before you begin: Set up your project and API key](https://ai.google.dev/gemini-api/docs/structured-output?lang=python#set-up-project-and-api-key)
    -   [Get and secure your API key](https://ai.google.dev/gemini-api/docs/structured-output?lang=python#get-and-secure-api-key)
    -   [Install the SDK package and configure your API key](https://ai.google.dev/gemini-api/docs/structured-output?lang=python#install-package-and-configure-key)
-   [Generate JSON](https://ai.google.dev/gemini-api/docs/structured-output?lang=python#generate-json)
    -   [Supply a schema as text in the prompt](https://ai.google.dev/gemini-api/docs/structured-output?lang=python#supply-schema-in-prompt)
    -   [Supply a schema through model configuration](https://ai.google.dev/gemini-api/docs/structured-output?lang=python#supply-schema-in-config)
-   [Use an enum to constrain output](https://ai.google.dev/gemini-api/docs/structured-output?lang=python#use-an-enum)
-   [More about JSON schemas](https://ai.google.dev/gemini-api/docs/structured-output?lang=python#json-schemas)
    -   [Property ordering](https://ai.google.dev/gemini-api/docs/structured-output?lang=python#property-ordering)

Python Node.js Go Dart (Flutter) Android Swift Web REST

  

Gemini generates unstructured text by default, but some applications require structured text. For these use cases, you can constrain Gemini to respond with JSON, a structured data format suitable for automated processing. You can also constrain the model to respond with one of the options specified in an enum.

Here are a few use cases that might require structured output from the model:

-   Build a database of companies by pulling company information out of newspaper articles.
-   Pull standardized information out of resumes.
-   Extract ingredients from recipes and display a link to a grocery website for each ingredient.

In your prompt, you can ask Gemini to produce JSON-formatted output, but note that the model is not guaranteed to produce JSON and nothing but JSON. For a more deterministic response, you can pass a specific JSON schema in a [`responseSchema`](https://ai.google.dev/api/rest/v1beta/GenerationConfig#FIELDS.response_schema) field so that Gemini always responds with an expected structure. To learn more about working with schemas, see [More about JSON schemas](https://ai.google.dev/gemini-api/docs/structured-output?lang=python#json-schemas).

This guide shows you how to generate JSON using the [`generateContent`](https://ai.google.dev/api/rest/v1/models/generateContent) method through the SDK of your choice or using the REST API directly. The examples show text-only input, although Gemini can also produce JSON responses to multimodal requests that include [images](https://ai.google.dev/gemini-api/docs/vision), [videos](https://ai.google.dev/gemini-api/docs/vision), and [audio](https://ai.google.dev/gemini-api/docs/audio).

## Before you begin: Set up your project and API key

Before calling the Gemini API, you need to set up your project and configure your API key.

**Expand to view how to set up your project and API key**

**Tip:** For complete setup instructions, see the [Gemini API quickstart](https://ai.google.dev/gemini-api/docs/quickstart).

### Get and secure your API key

You need an API key to call the Gemini API. If you don't already have one, create a key in Google AI Studio.

[Get an API key](https://aistudio.google.com/app/apikey)

It's strongly recommended that you do _not_ check an API key into your version control system.

You should store your API key in a secrets store such as Google Cloud [Secret Manager](https://cloud.google.com/secret-manager/docs).

This tutorial assumes that you're accessing your API key as an environment variable.

### Install the SDK package and configure your API key

**Note:** This section shows setup steps for a local Python environment. To install dependencies and configure your API key for Colab, see the [Authentication quickstart notebook](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Authentication.ipynb)

The Python SDK for the Gemini API is contained in the [`google-generativeai`](https://pypi.org/project/google-generativeai/) package.

1.  Install the dependency using pip:
    
    pip install -U google-generativeai
    
2.  Import the package and configure the service with your API key:
    
    import os
        import google.generativeai as genai
        
        genai.configure(api_key=os.environ['API_KEY'])

## Generate JSON

When the model is configured to output JSON, it responds to any prompt with JSON-formatted output.

You can control the structure of the JSON response by supplying a schema. There are two ways to supply a schema to the model:

-   As text in the prompt
-   As a structured schema supplied through model configuration

### Supply a schema as text in the prompt

The following example prompts the model to return cookie recipes in a specific JSON format.

Since the model gets the format specification from text in the prompt, you may have some flexibility in how you represent the specification. Any reasonable format for representing a JSON schema may work.

from google import genai
    
    prompt = """List a few popular cookie recipes in JSON format.
    
    Use this JSON schema:
    
    Recipe = {'recipe_name': str, 'ingredients': list[str]}
    Return: list[Recipe]"""
    
    client = genai.Client(api_key="GEMINI_API_KEY")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
    )
    
    # Use the response as a JSON string.
    print(response.text)

The output might look like this:

[
      {
        "recipe_name": "Chocolate Chip Cookies",
        "ingredients": [
          "2 1/4 cups all-purpose flour",
          "1 teaspoon baking soda",
          "1 teaspoon salt",
          "1 cup (2 sticks) unsalted butter, softened",
          "3/4 cup granulated sugar",
          "3/4 cup packed brown sugar",
          "1 teaspoon vanilla extract",
          "2 large eggs",
          "2 cups chocolate chips"
        ]
      },
      ...
    ]

### Supply a schema through model configuration

The following example does the following:

1.  Instantiates a model configured through a schema to respond with JSON.
2.  Prompts the model to return cookie recipes.

This more formal method for declaring the JSON schema gives you more precise control than relying just on text in the prompt.

**Important:** When you're working with JSON schemas in the Gemini API, the order of properties matters. For more information, see [Property ordering](https://ai.google.dev/gemini-api/docs/structured-output?lang=python#property-ordering).

from google import genai
    from pydantic import BaseModel
    
    
    class Recipe(BaseModel):
      recipe_name: str
      ingredients: list[str]
    
    
    client = genai.Client(api_key="GEMINI_API_KEY")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='List a few popular cookie recipes. Be sure to include the amounts of ingredients.',
        config={
            'response_mime_type': 'application/json',
            'response_schema': list[Recipe],
        },
    )
    # Use the response as a JSON string.
    print(response.text)
    
    # Use instantiated objects.
    my_recipes: list[Recipe] = response.parsed

The output might look like this:

[
      {
        "recipe_name": "Chocolate Chip Cookies",
        "ingredients": [
          "1 cup (2 sticks) unsalted butter, softened",
          "3/4 cup granulated sugar",
          "3/4 cup packed brown sugar",
          "1 teaspoon vanilla extract",
          "2 large eggs",
          "2 1/4 cups all-purpose flour",
          "1 teaspoon baking soda",
          "1 teaspoon salt",
          "2 cups chocolate chips"
        ]
      },
      ...
    ]

**Note:** [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/) are not yet supported. If a `pydantic.ValidationError` occurs, it is suppressed, and `.parsed` may be empty/null.

#### Schema Definition Syntax

Specify the schema for the JSON response in the `response_schema` property of your model configuration. The value of `response_schema` must be a either:

-   A type, as you would use in a type annotation. See the Python [`typing` module](https://docs.python.org/3/library/typing.html).
-   An instance of [`genai.types.Schema`](https://googleapis.github.io/python-genai/genai.html#genai.types.Schema).
-   The `dict` equivalent of `genai.types.Schema`.

##### Define a Schema with a Type

The easiest way to define a schema is with a direct type. This is the approach used in the preceding example:

config={'response_mime_type': 'application/json',
            'response_schema': list[Recipe]}

The Gemini API Python client library supports schemas defined with the following types (where `AllowedType` is any allowed type):

-   `int`
-   `float`
-   `bool`
-   `str`
-   `list[AllowedType]`
-   For structured types:
    -   `dict[str, AllowedType]`. This annotation declares all dict values to be the same type, but doesn't specify what keys should be included.
    -   User-defined [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/). This approach lets you specify the key names and define different types for the values associated with each of the keys, including nested structures.

## Use an enum to constrain output

In some cases you might want the model to choose a single option from a list of options. To implement this behavior, you can pass an _enum_ in your schema. You can use an enum option anywhere you could use a `str` in the `response_schema`, because an enum is a list of strings. Like a JSON schema, an enum lets you constrain model output to meet the requirements of your application.

For example, assume that you're developing an application to classify musical instruments into one of five categories: `"Percussion"`, `"String"`, `"Woodwind"`, `"Brass"`, or "`"Keyboard"`". You could create an enum to help with this task.

In the following example, you pass the enum class `Instrument` as the `response_schema`, and the model should choose the most appropriate enum option.

from google import genai
    import enum
    
    class Instrument(enum.Enum):
      PERCUSSION = "Percussion"
      STRING = "String"
      WOODWIND = "Woodwind"
      BRASS = "Brass"
      KEYBOARD = "Keyboard"
    
    client = genai.Client(api_key="GEMINI_API_KEY")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='What type of instrument is an oboe?',
        config={
            'response_mime_type': 'text/x.enum',
            'response_schema': Instrument,
        },
    )
    
    print(response.text)
    # Woodwind

The Python SDK will translate the type declarations for the API. However, the API accepts a subset of the OpenAPI 3.0 schema ([Schema](https://ai.google.dev/api/caching#schema)). You can also pass the schema as JSON:

from google import genai
    
    client = genai.Client(api_key="GEMINI_API_KEY")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='What type of instrument is an oboe?',
        config={
            'response_mime_type': 'text/x.enum',
            'response_schema': {
                "type": "STRING",
                "enum": ["Percussion", "String", "Woodwind", "Brass", "Keyboard"],
            },
        },
    )
    
    print(response.text)
    # Woodwind

Beyond basic multiple choice problems, you can use an enum anywhere in a schema for JSON or function calling. For example, you could ask the model for a list of recipe titles and use a `Grade` enum to give each title a popularity grade:

from google import genai
    
    import enum
    from pydantic import BaseModel
    
    class Grade(enum.Enum):
        A_PLUS = "a+"
        A = "a"
        B = "b"
        C = "c"
        D = "d"
        F = "f"
    
    class Recipe(BaseModel):
      recipe_name: str
      rating: Grade
    
    client = genai.Client(api_key="GEMINI_API_KEY")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='List 10 home-baked cookies and give them grades based on tastiness.',
        config={
            'response_mime_type': 'application/json',
            'response_schema': list[Recipe],
        },
    )
    
    print(response.text)
    # [{"rating": "a+", "recipe_name": "Classic Chocolate Chip Cookies"}, ...]

## More about JSON schemas

When you configure the model to return a JSON response, you can use a `Schema` object to define the shape of the JSON data. The `Schema` represents a select subset of the [OpenAPI 3.0 Schema object](https://spec.openapis.org/oas/v3.0.3#schema-object).

Here's a pseudo-JSON representation of all the `Schema` fields:

{
      "type": enum (Type),
      "format": string,
      "description": string,
      "nullable": boolean,
      "enum": [
        string
      ],
      "maxItems": string,
      "minItems": string,
      "properties": {
        string: {
          object (Schema)
        },
        ...
      },
      "required": [
        string
      ],
      "propertyOrdering": [
        string
      ],
      "items": {
        object (Schema)
      }
    }

The `Type` of the schema must be one of the OpenAPI [Data Types](https://spec.openapis.org/oas/v3.0.3#data-types). Only a subset of fields is valid for each `Type`. The following list maps each `Type` to valid fields for that type:

-   `string` -> enum, format
-   `integer` -> format
-   `number` -> format
-   `bool`
-   `array` -> minItems, maxItems, items
-   `object` -> properties, required, propertyOrdering, nullable

Here are some example schemas showing valid type-and-field combinations:

{ "type": "string", "enum": ["a", "b", "c"] }
    
    { "type": "string", "format": "date-time" }
    
    { "type": "integer", "format": "int64" }
    
    { "type": "number", "format": "double" }
    
    { "type": "bool" }
    
    { "type": "array", "minItems": 3, "maxItems": 3, "items": { "type": ... } }
    
    { "type": "object",
      "properties": {
        "a": { "type": ... },
        "b": { "type": ... },
        "c": { "type": ... }
      },
      "nullable": true,
      "required": ["c"],
      "propertyOrdering": ["c", "b", "a"]
    }

For complete documentation of the Schema fields as they're used in the Gemini API, see the [Schema reference](https://ai.google.dev/api/caching#Schema).

### Property ordering

When you're working with JSON schemas in the Gemini API, the order of properties is important. By default, the API orders properties alphabetically and does not preserve the order in which the properties are defined (although the [Google Gen AI SDKs](https://ai.google.dev/gemini-api/docs/sdks) may preserve this order). If you're providing examples to the model with a schema configured, and the property ordering of the examples is not consistent with the property ordering of the schema, the output could be rambling or unexpected.

To ensure a consistent, predictable ordering of properties, you can use the optional `propertyOrdering[]` field.

"propertyOrdering": ["recipe_name", "ingredients"]

`propertyOrdering[]` – not a standard field in the OpenAPI specification – is an array of strings used to determine the order of properties in the response. By specifying the order of properties and then providing examples with properties in that same order, you can potentially improve the quality of results.

# Intro to function calling with the Gemini API

-   On this page
-   [How function calling works](https://ai.google.dev/gemini-api/docs/function-calling#how_it_works)
-   [Function declarations](https://ai.google.dev/gemini-api/docs/function-calling#function_declarations)
    -   [Best practices for function declarations](https://ai.google.dev/gemini-api/docs/function-calling#key-parameters-best-practices)
-   [Function calling mode](https://ai.google.dev/gemini-api/docs/function-calling#function_calling_mode)
-   [Compositional function calling](https://ai.google.dev/gemini-api/docs/function-calling#compositional-function-calling)
-   [Multi-tool use](https://ai.google.dev/gemini-api/docs/function-calling#multi-tool-use)
-   [Function calling examples](https://ai.google.dev/gemini-api/docs/function-calling#function-calling-curl-samples)
    -   [Single-turn example](https://ai.google.dev/gemini-api/docs/function-calling#function-calling-single-turn-curl-sample)
    -   [Single-turn example using ANY mode](https://ai.google.dev/gemini-api/docs/function-calling#single-turn-any-mode)
    -   [Single-turn example using ANY mode and allowed functions](https://ai.google.dev/gemini-api/docs/function-calling#single-turn-using-mode-and-allowed-functions)
    -   [Multi-turn examples](https://ai.google.dev/gemini-api/docs/function-calling#function-calling-one-and-a-half-turn-curl-sample)
-   [Best practices](https://ai.google.dev/gemini-api/docs/function-calling#best-practices)
    -   [User prompt](https://ai.google.dev/gemini-api/docs/function-calling#prompt-best-practices)
    -   [Sampling parameters](https://ai.google.dev/gemini-api/docs/function-calling#sampling-parameters-best-practices)
    -   [API invocation](https://ai.google.dev/gemini-api/docs/function-calling#invoke-api-best-practices)

Using the Gemini API function calling feature, you can provide custom function definitions to the model. The model doesn't directly invoke these functions, but instead generates structured output that specifies a function name and suggested arguments. You can then use the function name and arguments to call an external API, and you can incorporate the resulting API output into a further query to the model, enabling the model to provide a more comprehensive response and take additional actions.

Function calling empowers users to interact with real-time information and services like databases, customer relationship management systems, and document repositories. The feature also enhances the model's ability to provide relevant and contextual answers. Function calling is best for interacting with external systems. If your use case requires the model to perform computation but doesn't involve external systems or APIs, you should consider using [code execution](https://ai.google.dev/gemini-api/docs/code-execution) instead.

For a working example of function calling, see the ["light bot" notebook](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Function_calling_config.ipynb).

**Beta:** The function calling feature is in Beta release. For more information, see the [API versions](https://ai.google.dev/docs/api_versions) page.

## How function calling works

You use the function calling feature by adding structured query data describing programing interfaces, called _function declarations_, to a model prompt. The function declarations provide the name of the API function, explain its purpose, any parameters it supports, and descriptions of those parameters. After you pass a list of function declarations in a query to the model, it analyzes function declarations and the rest of the query to determine how to use the declared API in response to the request.

The model then returns an object in an [OpenAPI compatible schema](https://spec.openapis.org/oas/v3.0.3#schema) specifying how to call one or more of the declared functions in order to respond to the user's question. You can then take the recommended function call parameters, call the actual API, get a response, and provide that response to the user or take further action. Note that the model doesn't actually call the declared functions. Instead, you use the returned schema object parameters to call the function. The Gemini API also supports parallel function calling, where the model recommends multiple API function calls based on a single request.

## Function declarations

When you implement function calling in a prompt, you create a `tools` object, which contains one or more _`function declarations`_. You define functions using JSON, specifically with a [select subset](https://ai.google.dev/api/caching#Schema) of the [OpenAPI schema](https://spec.openapis.org/oas/v3.0.3#schemawr) format. A single function declaration can include the following parameters:

-   **`name`** (string): The unique identifier for the function within the API call.
-   **`description`** (string): A comprehensive explanation of the function's purpose and capabilities.
-   **`parameters`** (object): Defines the input data required by the function.
    -   **`type`** (string): Specifies the overall data type, such as `object`.
    -   **`properties`** (object): Lists individual parameters, each with:
        -   **`type`** (string): The data type of the parameter, such as `string`, `integer`, `boolean`.
        -   **`description`** (string): A clear explanation of the parameter's purpose and expected format.
    -   **`required`** (array): An array of strings listing the parameter names that are mandatory for the function to operate.

For code examples of a function declaration using cURL commands, see the [Function calling examples](https://ai.google.dev/gemini-api/docs/function-calling#function-calling-curl-samples). For examples of creating function declarations using the Gemini API SDKs, see the [Function calling tutorial](https://ai.google.dev/gemini-api/docs/function-calling/tutorial).

### Best practices for function declarations

Accurately defining your functions is essential when integrating them into your requests. Each function relies on specific parameters that guide its behavior and interaction with the model. The following listing provides guidance on defining the parameters of an individual function in a `functions_declarations` array.

-   **`name`**: Use clear, descriptive names without space, period (`.`), or dash (`-`) characters. Instead, use underscore (`_`) characters or camel case.
    
-   **`description`**: Provide detailed, clear, and specific function descriptions, providing examples if necessary. For example, instead of `find theaters`, use `find theaters based on location and optionally movie title that is currently playing in theaters.` Avoid overly broad or ambiguous descriptions.
    
-   **`properties` > `type`**: Use strongly typed parameters to reduce model hallucinations. For example, if the parameter values are from a finite set, use an `enum` field instead of listing the values in the description (e.g., `"type": "enum", "values": ["now_playing", "upcoming"]`). If the parameter value is always an integer, set the type to `integer` rather than `number`.
    
-   **`properties` > `description`**: Provide concrete examples and constraints. For example, instead of `the location to search`, use `The city and state, e.g. San Francisco, CA or a zip code e.g. 95616`.
    

For more best practices when using function calling, see the [Best Practices](https://ai.google.dev/gemini-api/docs/function-calling#best-practices) section.

## Function calling mode

You can use the function calling _`mode`_ parameter to modify the execution behavior of the feature. There are three modes available:

-   **`AUTO`**: The default model behavior. The model decides to predict either a function call or a natural language response.
-   **`ANY`**: The model is constrained to always predict a function call. If `allowed_function_names` is _not_ provided, the model picks from all of the available function declarations. If `allowed_function_names` _is_ provided, the model picks from the set of allowed functions.
-   **`NONE`**: The model won't predict a function call. In this case, the model behavior is the same as if you don't pass any function declarations.

You can also pass a set of `allowed_function_names` that, when provided, limits the functions that the model will call. You should only include `allowed_function_names` when the mode is `ANY`. Function names should match function declaration names. With the mode set to `ANY` and the `allowed_function_names` set, the model will predict a function call from the set of function names provided.

**Key Point:** If you set the mode to `ANY` and provide `allowed_function_names`, the model picks from the set of allowed functions. If you set the mode to `ANY` and _don't_ provide `allowed_function_names`, the model picks from all of the available functions.

The following code snippet from an [example request](https://ai.google.dev/gemini-api/docs/function-calling#single-turn-using-mode-and-allowed-functions) shows how to set the `mode` to `ANY` and specify a list of allowed functions:

"tool_config": {
      "function_calling_config": {
        "mode": "ANY",
        "allowed_function_names": ["find_theaters", "get_showtimes"]
      },
    }

## Compositional function calling

Gemini 2.0 supports a new function calling capability: _compositional function calling_. Compositional function calling enables the Gemini API to invoke multiple user-defined functions automatically in the process of generating a response. For example, to respond to the prompt `"Get the temperature in my current location"`, the Gemini API might invoke both a `get_current_location()` function and a `get_weather()` function that takes the location as a parameter.

Compositional function calling with code execution requires bidirectional streaming and is only supported by the new Multimodal Live API. Here's an example showing how you might use compositional function calling, code execution, and the Multimodal Live API together:

**Note:** The `run()` function declaration, which handles the asynchronous websocket setup, is omitted for brevity.

turn_on_the_lights_schema = {'name': 'turn_on_the_lights'}
    turn_off_the_lights_schema = {'name': 'turn_off_the_lights'}
    
    prompt = """
      Hey, can you write run some python code to turn on the lights, wait 10s and then turn off the lights?
      """
    
    tools = [
        {'code_execution': {}},
        {'function_declarations': [turn_on_the_lights_schema, turn_off_the_lights_schema]}
    ]
    
    await run(prompt, tools=tools, modality="AUDIO")

Python developers can try this out in the [Live API Tool Use notebook](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_LiveAPI_tools.ipynb).

## Multi-tool use

**Note:** Multi-tool use is only supported by the [Multimodal Live API](https://ai.google.dev/api/multimodal-live).

With Gemini 2.0, you can enable multiple tools at the same time, and the model will decide when to call them. Here's an example that enables two tools, Grounding with Google Search and code execution, in a request using the Multimodal Live API.

**Note:** The `run()` function declaration, which handles the asynchronous websocket setup, is omitted for brevity. Additionally, multi-tool use is now supported only through the Multimodal Live API.

prompt = """
      Hey, I need you to do three things for me.
    
      1. Turn on the lights.
      2. Then compute the largest prime palindrome under 100000.
      3. Then use Google Search to look up information about the largest earthquake in California the week of Dec 5 2024.
    
      Thanks!
      """
    
    tools = [
        {'google_search': {}},
        {'code_execution': {}},
        {'function_declarations': [turn_on_the_lights_schema, turn_off_the_lights_schema]}
    ]
    
    await run(prompt, tools=tools, modality="AUDIO")

Python developers can try this out in the [Live API Tool Use notebook](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_LiveAPI_tools.ipynb).

## Function calling examples

This section provides example prompts for function calling using cURL commands. The examples include single turn and multiple-turn scenarios, and enabling different function calling modes.

When using cURL commands with this feature, the function and parameter information is included in the `tools` element. Each function declaration in the `tools` element contains the function name, and you specify the parameters using an [OpenAPI compatible schema](https://spec.openapis.org/oas/v3.0.3#schema), and a function description.

### Single-turn example

Single-turn is when you call the language model one time. With function calling, a single-turn use case might be when you provide the model a natural language query and a list of functions. In this case, the model uses the function declaration, which includes the function name, parameters, and description, to predict which function to call and the arguments to call it with.

The following curl sample is an example of passing in a description of a function that returns information about where a movie is playing. Several function declarations are included in the request, such as `find_movies` and `find_theaters`.

#### Single-turn function calling example request

curl https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=$API\_KEY \\
  -H 'Content-Type: application/json' \\
  -d '{
    "contents": {
      "role": "user",
      "parts": {
        "text": "Which theaters in Mountain View show Barbie movie?"
    }
  },
  "tools": \[
    {
      "function\_declarations": \[
        {
          "name": "find\_movies",
          "description": "find movie titles currently playing in theaters based on any description, genre, title words, etc.",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
              },
              "description": {
                "type": "string",
                "description": "Any kind of description including category or genre, title words, attributes, etc."
              }
            },
            "required": \[
              "description"
            \]
          }
        },
        {
          "name": "find\_theaters",
          "description": "find theaters based on location and optionally movie title which is currently playing in theaters",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
              },
              "movie": {
                "type": "string",
                "description": "Any movie title"
              }
            },
            "required": \[
              "location"
            \]
          }
        },
        {
          "name": "get\_showtimes",
          "description": "Find the start times for movies playing in a specific theater",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
              },
              "movie": {
                "type": "string",
                "description": "Any movie title"
              },
              "theater": {
                "type": "string",
                "description": "Name of the theater"
              },
              "date": {
                "type": "string",
                "description": "Date for requested showtime"
              }
            },
            "required": \[
              "location",
              "movie",
              "theater",
              "date"
            \]
          }
        }
      \]
    }
  \]
}'
    

The response to this curl example might be similar to the following.

#### Single-turn function calling curl example response

\[{
  "candidates": \[
    {
      "content": {
        "parts": \[
          {
            "functionCall": {
              "name": "find\_theaters",
              "args": {
                "movie": "Barbie",
                "location": "Mountain View, CA"
              }
            }
          }
        \]
      },
      "finishReason": "STOP",
      "safetyRatings": \[
        {
          "category": "HARM\_CATEGORY\_HARASSMENT",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM\_CATEGORY\_HATE\_SPEECH",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM\_CATEGORY\_SEXUALLY\_EXPLICIT",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM\_CATEGORY\_DANGEROUS\_CONTENT",
          "probability": "NEGLIGIBLE"
        }
      \]
    }
  \],
  "usageMetadata": {
    "promptTokenCount": 9,
    "totalTokenCount": 9
  }
}\]
    

### Single-turn example using ANY mode

The following curl example is similar to the [single-turn example](https://ai.google.dev/gemini-api/docs/function-calling#function-calling-single-turn-curl-sample), but it sets the [mode](https://ai.google.dev/gemini-api/docs/function-calling#function_calling_mode) to `ANY`:

"tool_config": {
      "function_calling_config": {
        "mode": "ANY"
      },
    }

#### Single-turn function calling using ANY mode (request)

curl https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=$API\_KEY \\
  -H 'Content-Type: application/json' \\
  -d '{
    "contents": {
      "role": "user",
      "parts": {
        "text": "What movies are showing in North Seattle tonight?"
    }
  },
  "tools": \[
    {
      "function\_declarations": \[
        {
          "name": "find\_movies",
          "description": "find movie titles currently playing in theaters based on any description, genre, title words, etc.",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
              },
              "description": {
                "type": "string",
                "description": "Any kind of description including category or genre, title words, attributes, etc."
              }
            },
            "required": \[
              "description"
            \]
          }
        },
        {
          "name": "find\_theaters",
          "description": "find theaters based on location and optionally movie title which is currently playing in theaters",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
              },
              "movie": {
                "type": "string",
                "description": "Any movie title"
              }
            },
            "required": \[
              "location"
            \]
          }
        },
        {
          "name": "get\_showtimes",
          "description": "Find the start times for movies playing in a specific theater",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
              },
              "movie": {
                "type": "string",
                "description": "Any movie title"
              },
              "theater": {
                "type": "string",
                "description": "Name of the theater"
              },
              "date": {
                "type": "string",
                "description": "Date for requested showtime"
              }
            },
            "required": \[
              "location",
              "movie",
              "theater",
              "date"
            \]
          }
        }
      \]
    }
  \],
  "tool\_config": {
    "function\_calling\_config": {
      "mode": "ANY"
    },
  }
}'
    

The response might be similar to the following:

#### Single-turn function calling using ANY mode (response)

{
  "candidates": \[
    {
      "content": {
        "parts": \[
          {
            "functionCall": {
              "name": "find\_movies",
              "args": {
                "description": "",
                "location": "North Seattle, WA"
              }
            }
          }
        \],
        "role": "model"
      },
      "finishReason": "STOP",
      "index": 0,
      "safetyRatings": \[
        {
          "category": "HARM\_CATEGORY\_DANGEROUS\_CONTENT",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM\_CATEGORY\_HARASSMENT",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM\_CATEGORY\_HATE\_SPEECH",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM\_CATEGORY\_SEXUALLY\_EXPLICIT",
          "probability": "NEGLIGIBLE"
        }
      \]
    }
  \],
  "promptFeedback": {
    "safetyRatings": \[
      {
        "category": "HARM\_CATEGORY\_SEXUALLY\_EXPLICIT",
        "probability": "NEGLIGIBLE"
      },
      {
        "category": "HARM\_CATEGORY\_HATE\_SPEECH",
        "probability": "NEGLIGIBLE"
      },
      {
        "category": "HARM\_CATEGORY\_HARASSMENT",
        "probability": "NEGLIGIBLE"
      },
      {
        "category": "HARM\_CATEGORY\_DANGEROUS\_CONTENT",
        "probability": "NEGLIGIBLE"
      }
    \]
  }
}
    

### Single-turn example using ANY mode and allowed functions

The following curl example is similar to the [single-turn example](https://ai.google.dev/gemini-api/docs/function-calling#function-calling-single-turn-curl-sample), but it sets the [mode](https://ai.google.dev/gemini-api/docs/function-calling#function_calling_mode) to `ANY` and includes a list of allowed functions:

"tool_config": {
      "function_calling_config": {
        "mode": "ANY",
        "allowed_function_names": ["find_theaters", "get_showtimes"]
      },
    }

#### Single-turn function calling using ANY mode and allowed functions (request)

curl https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=$API\_KEY \\
  -H 'Content-Type: application/json' \\
  -d '{
    "contents": {
      "role": "user",
      "parts": {
        "text": "What movies are showing in North Seattle tonight?"
    }
  },
  "tools": \[
    {
      "function\_declarations": \[
        {
          "name": "find\_movies",
          "description": "find movie titles currently playing in theaters based on any description, genre, title words, etc.",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
              },
              "description": {
                "type": "string",
                "description": "Any kind of description including category or genre, title words, attributes, etc."
              }
            },
            "required": \[
              "description"
            \]
          }
        },
        {
          "name": "find\_theaters",
          "description": "find theaters based on location and optionally movie title which is currently playing in theaters",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
              },
              "movie": {
                "type": "string",
                "description": "Any movie title"
              }
            },
            "required": \[
              "location"
            \]
          }
        },
        {
          "name": "get\_showtimes",
          "description": "Find the start times for movies playing in a specific theater",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
              },
              "movie": {
                "type": "string",
                "description": "Any movie title"
              },
              "theater": {
                "type": "string",
                "description": "Name of the theater"
              },
              "date": {
                "type": "string",
                "description": "Date for requested showtime"
              }
            },
            "required": \[
              "location",
              "movie",
              "theater",
              "date"
            \]
          }
        }
      \]
    }
  \],
  "tool\_config": {
    "function\_calling\_config": {
      "mode": "ANY",
      "allowed\_function\_names": \["find\_theaters", "get\_showtimes"\]
    },
  }
}'
    

The model can't predict the `find_movies` function, because it's not on the list of allowed functions, so it predicts a different function instead. The response might be similar to the following:

#### Single-turn function calling using ANY mode and allowed functions (response)

{
  "candidates": \[
    {
      "content": {
        "parts": \[
          {
            "functionCall": {
              "name": "find\_theaters",
              "args": {
                "location": "North Seattle, WA",
                "movie": null
              }
            }
          }
        \],
        "role": "model"
      },
      "finishReason": "STOP",
      "index": 0,
      "safetyRatings": \[
        {
          "category": "HARM\_CATEGORY\_SEXUALLY\_EXPLICIT",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM\_CATEGORY\_HARASSMENT",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM\_CATEGORY\_HATE\_SPEECH",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM\_CATEGORY\_DANGEROUS\_CONTENT",
          "probability": "NEGLIGIBLE"
        }
      \]
    }
  \],
  "promptFeedback": {
    "safetyRatings": \[
      {
        "category": "HARM\_CATEGORY\_SEXUALLY\_EXPLICIT",
        "probability": "NEGLIGIBLE"
      },
      {
        "category": "HARM\_CATEGORY\_HATE\_SPEECH",
        "probability": "NEGLIGIBLE"
      },
      {
        "category": "HARM\_CATEGORY\_HARASSMENT",
        "probability": "NEGLIGIBLE"
      },
      {
        "category": "HARM\_CATEGORY\_DANGEROUS\_CONTENT",
        "probability": "NEGLIGIBLE"
      }
    \]
  }
}
    

### Multi-turn examples

You can implement a multi-turn function calling scenario by doing the following:

1.  Get a function call response by calling the language model. This is the first turn.
2.  Call the language model using the function call response from the first turn and the function response you get from calling that function. This is the second turn.

The response from the second turn either summarizes the results to answer your query in the first turn, or contains a second function call you can use to get more information for your query.

This topic includes two multi-turn curl examples:

-   [Curl example that uses a function response from a previous turn](https://ai.google.dev/gemini-api/docs/function-calling#multi-turn-example-1)
-   [Curl example that calls a language model multiple times](https://ai.google.dev/gemini-api/docs/function-calling#multi-turn-example-2)

#### Use a response from a previous turn

The following curl sample calls the function and arguments returned by the previous single-turn example to get a response. The method and parameters returned by the single-turn example are in this JSON.

"functionCall": {
      "name": "find_theaters",
      "args": {
        "movie": "Barbie",
        "location": "Mountain View, CA"
      }
    }

#### Multi-turn function calling curl example request

curl https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=$API\_KEY \\
  -H 'Content-Type: application/json' \\
  -d '{
    "contents": \[{
      "role": "user",
      "parts": \[{
        "text": "Which theaters in Mountain View show Barbie movie?"
    }\]
  }, {
    "role": "model",
    "parts": \[{
      "functionCall": {
        "name": "find\_theaters",
        "args": {
          "location": "Mountain View, CA",
          "movie": "Barbie"
        }
      }
    }\]
  }, {
    "role": "user",
    "parts": \[{
      "functionResponse": {
        "name": "find\_theaters",
        "response": {
          "name": "find\_theaters",
          "content": {
            "movie": "Barbie",
            "theaters": \[{
              "name": "AMC Mountain View 16",
              "address": "2000 W El Camino Real, Mountain View, CA 94040"
            }, {
              "name": "Regal Edwards 14",
              "address": "245 Castro St, Mountain View, CA 94040"
            }\]
          }
        }
      }
    }\]
  }\],
  "tools": \[{
    "functionDeclarations": \[{
      "name": "find\_movies",
      "description": "find movie titles currently playing in theaters based on any description, genre, title words, etc.",
      "parameters": {
        "type": "OBJECT",
        "properties": {
          "location": {
            "type": "STRING",
            "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
          },
          "description": {
            "type": "STRING",
            "description": "Any kind of description including category or genre, title words, attributes, etc."
          }
        },
        "required": \["description"\]
      }
    }, {
      "name": "find\_theaters",
      "description": "find theaters based on location and optionally movie title which is currently playing in theaters",
      "parameters": {
        "type": "OBJECT",
        "properties": {
          "location": {
            "type": "STRING",
            "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
          },
          "movie": {
            "type": "STRING",
            "description": "Any movie title"
          }
        },
        "required": \["location"\]
      }
    }, {
      "name": "get\_showtimes",
      "description": "Find the start times for movies playing in a specific theater",
      "parameters": {
        "type": "OBJECT",
        "properties": {
          "location": {
            "type": "STRING",
            "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
          },
          "movie": {
            "type": "STRING",
            "description": "Any movie title"
          },
          "theater": {
            "type": "STRING",
            "description": "Name of the theater"
          },
          "date": {
            "type": "STRING",
            "description": "Date for requested showtime"
          }
        },
        "required": \["location", "movie", "theater", "date"\]
      }
    }\]
  }\]
}'
    

The response to this curl example includes the result of calling the `find_theaters` method. The response might be similar to the following:

#### Multi-turn function calling curl example response

{
  "candidates": \[
    {
      "content": {
        "parts": \[
          {
            "text": " OK. Barbie is showing in two theaters in Mountain View, CA: AMC Mountain View 16 and Regal Edwards 14."
          }
        \]
      }
    }
  \],
  "usageMetadata": {
    "promptTokenCount": 9,
    "candidatesTokenCount": 27,
    "totalTokenCount": 36
  }
}
    

#### Call the model multiple times

The following cURL example calls the generative AI model multiple times to call a function. Each time the model calls the function, it can use a different function to answer a different user query in the request.

#### Multi-turn function calling curl example request

curl https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=$API\_KEY \\
  -H 'Content-Type: application/json' \\
  -d '{
    "contents": \[{
      "role": "user",
      "parts": \[{
        "text": "Which theaters in Mountain View show Barbie movie?"
    }\]
  }, {
    "role": "model",
    "parts": \[{
      "functionCall": {
        "name": "find\_theaters",
        "args": {
          "location": "Mountain View, CA",
          "movie": "Barbie"
        }
      }
    }\]
  }, {
    "role": "user",
    "parts": \[{
      "functionResponse": {
        "name": "find\_theaters",
        "response": {
          "name": "find\_theaters",
          "content": {
            "movie": "Barbie",
            "theaters": \[{
              "name": "AMC Mountain View 16",
              "address": "2000 W El Camino Real, Mountain View, CA 94040"
            }, {
              "name": "Regal Edwards 14",
              "address": "245 Castro St, Mountain View, CA 94040"
            }\]
          }
        }
      }
    }\]
  },
  {
    "role": "model",
    "parts": \[{
      "text": " OK. Barbie is showing in two theaters in Mountain View, CA: AMC Mountain View 16 and Regal Edwards 14."
    }\]
  },{
    "role": "user",
    "parts": \[{
      "text": "Can we recommend some comedy movies on show in Mountain View?"
    }\]
  }\],
  "tools": \[{
    "functionDeclarations": \[{
      "name": "find\_movies",
      "description": "find movie titles currently playing in theaters based on any description, genre, title words, etc.",
      "parameters": {
        "type": "OBJECT",
        "properties": {
          "location": {
            "type": "STRING",
            "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
          },
          "description": {
            "type": "STRING",
            "description": "Any kind of description including category or genre, title words, attributes, etc."
          }
        },
        "required": \["description"\]
      }
    }, {
      "name": "find\_theaters",
      "description": "find theaters based on location and optionally movie title which is currently playing in theaters",
      "parameters": {
        "type": "OBJECT",
        "properties": {
          "location": {
            "type": "STRING",
            "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
          },
          "movie": {
            "type": "STRING",
            "description": "Any movie title"
          }
        },
        "required": \["location"\]
      }
    }, {
      "name": "get\_showtimes",
      "description": "Find the start times for movies playing in a specific theater",
      "parameters": {
        "type": "OBJECT",
        "properties": {
          "location": {
            "type": "STRING",
            "description": "The city and state, e.g. San Francisco, CA or a zip code e.g. 95616"
          },
          "movie": {
            "type": "STRING",
            "description": "Any movie title"
          },
          "theater": {
            "type": "STRING",
            "description": "Name of the theater"
          },
          "date": {
            "type": "STRING",
            "description": "Date for requested showtime"
          }
        },
        "required": \["location", "movie", "theater", "date"\]
      }
    }\]
  }\]
}'
    

#### Multi-turn function calling curl example response

\[{
  "candidates": \[
    {
      "content": {
        "parts": \[
          {
            "functionCall": {
              "name": "find\_movies",
              "args": {
                "description": "comedy",
                "location": "Mountain View, CA"
              }
            }
          }
        \]
      },
      "finishReason": "STOP",
      "safetyRatings": \[
        {
          "category": "HARM\_CATEGORY\_HARASSMENT",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM\_CATEGORY\_HATE\_SPEECH",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM\_CATEGORY\_SEXUALLY\_EXPLICIT",
          "probability": "NEGLIGIBLE"
        },
        {
          "category": "HARM\_CATEGORY\_DANGEROUS\_CONTENT",
          "probability": "NEGLIGIBLE"
        }
      \]
    }
  \],
  "usageMetadata": {
    "promptTokenCount": 48,
    "totalTokenCount": 48
  }
}
\]
    

## Best practices

Follow these best practices to improve the accuracy and reliability of your function calls.

### User prompt

For best results, prepend the user query with the following details:

-   Additional context for the model. For example, `You are a movie API assistant to help users find movies and showtimes based on their preferences.`
-   Details or instructions on how and when to use the functions. For example, `Don't make assumptions on showtimes. Always use a future date for showtimes.`
-   Instructions to ask clarifying questions if user queries are ambiguous. For example, `Ask clarifying questions if not enough information is available to complete the request.`

### Sampling parameters

For the temperature parameter, use `0` or another low value. This instructs the model to generate more confident results and reduces hallucinations.

### API invocation

If the model proposes the invocation of a function that would send an order, update a database, or otherwise have significant consequences, validate the function call with the user before executing it.

# Grounding with Google Search

-   On this page
-   [Configure Search Grounding](https://ai.google.dev/gemini-api/docs/grounding?lang=python#configure-search)
-   [Google Search Suggestions](https://ai.google.dev/gemini-api/docs/grounding?lang=python#search-suggestions)
-   [Google Search retrieval](https://ai.google.dev/gemini-api/docs/grounding?lang=python#google-search-retrieval)
    -   [Getting started](https://ai.google.dev/gemini-api/docs/grounding?lang=python#getting-started)
    -   [Dynamic threshold](https://ai.google.dev/gemini-api/docs/grounding?lang=python#dynamic-threshold)
    -   [Dynamic retrieval](https://ai.google.dev/gemini-api/docs/grounding?lang=python#dynamic-retrieval)
-   [A grounded response](https://ai.google.dev/gemini-api/docs/grounding?lang=python#grounded-response)

Python Node.js REST

The Grounding with Google Search feature in the Gemini API and AI Studio can be used to improve the accuracy and recency of responses from the model. In addition to more factual responses, when Grounding with Google Search is enabled, the Gemini API returns grounding sources (in-line supporting links) and [Google Search Suggestions](https://ai.google.dev/gemini-api/docs/grounding?lang=python#search-suggestions) along with the response content. The Search Suggestions point users to the search results corresponding to the grounded response.

This guide will help you get started with Grounding with Google Search using one of the Gemini API SDKs or the REST API.

## Configure Search Grounding

Starting with Gemini 2.0, Google Search is available as a tool. This means that the model can decide when to use Google Search. The following example shows how to configure Search as a tool.

from google import genai
    from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
    
    client = genai.Client()
    model_id = "gemini-2.0-flash"
    
    google_search_tool = Tool(
        google_search = GoogleSearch()
    )
    
    response = client.models.generate_content(
        model=model_id,
        contents="When is the next total solar eclipse in the United States?",
        config=GenerateContentConfig(
            tools=[google_search_tool],
            response_modalities=["TEXT"],
        )
    )
    
    for each in response.candidates[0].content.parts:
        print(each.text)
    # Example response:
    # The next total solar eclipse visible in the contiguous United States will be on ...
    
    # To get grounding metadata as web content.
    print(response.candidates[0].grounding_metadata.search_entry_point.rendered_content)

The Search-as-a-tool functionality also enables multi-turn searches and multi-tool queries (for example, combining Grounding with Google Search and code execution).

Search as a tool enables complex prompts and workflows that require planning, reasoning, and thinking:

-   Grounding to enhance factuality and recency and provide more accurate answers
-   Retrieving artifacts from the web to do further analysis on
-   Finding relevant images, videos, or other media to assist in multimodal reasoning or generation tasks
-   Coding, technical troubleshooting, and other specialized tasks
-   Finding region-specific information or assisting in translating content accurately
-   Finding relevant websites for further browsing

Grounding with Google Search works with all [available languages](https://ai.google.dev/gemini-api/docs/models/gemini#available-languages) when doing text prompts. On the paid tier of the Gemini Developer API, you can get 1,500 Grounding with Google Search queries per day for free, with additional queries billed at the standard $35 per 1,000 queries.

You can learn more by [trying the Search tool notebook](https://colab.research.google.com/github/google-gemini/cookbook/blob/main/quickstarts/Search_Grounding.ipynb).

## Google Search Suggestions

To use Grounding with Google Search, you have to display Google Search Suggestions, which are suggested queries included in the metadata of the grounded response. To learn more about the display requirements, see [Use Google Search Suggestions](https://ai.google.dev/gemini-api/docs/grounding/search-suggestions).

## Google Search retrieval

**Note:** Google Search retrieval is only compatible with Gemini 1.5 models. For Gemini 2.0 models, you should use Search as a tool.

To configure a model to use Google Search retrieval, pass in the appropriate tool.

### Getting started

from google import genai
    from google.genai import types
    
    client = genai.Client(api_key="GEMINI_API_KEY")
    
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents="Who won Wimbledon this year?",
        config=types.GenerateContentConfig(
            tools=[types.Tool(
                google_search=types.GoogleSearchRetrieval
            )]
        )
    )
    print(response)

### Dynamic threshold

The `dynamic_threshold` settings let you control the [retrieval behavior](https://ai.google.dev/gemini-api/docs/grounding?lang=python#dynamic-retrieval), giving you additional control over when Grounding with Google Search is used.

from google import genai
    from google.genai import types
    
    client = genai.Client(api_key="GEMINI_API_KEY")
    
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents="Who won Wimbledon this year?",
        config=types.GenerateContentConfig(
            tools=[types.Tool(
                google_search=types.GoogleSearchRetrieval(
                    dynamic_retrieval_config=types.DynamicRetrievalConfig(
                        dynamic_threshold=0.6))
            )]
        )
    )
    print(response)

### Dynamic retrieval

**Note:** Dynamic retrieval is only compatible with Gemini 1.5 Flash. For Gemini 2.0, you should use Search as a tool, as shown above.

Some queries are likely to benefit more from Grounding with Google Search than others. The _dynamic retrieval_ feature gives you additional control over when to use Grounding with Google Search.

If the dynamic retrieval mode is unspecified, Grounding with Google Search is always triggered. If the mode is set to dynamic, the model decides when to use grounding based on a threshold that you can configure. The threshold is a floating-point value in the range \[0,1\] and defaults to 0.3. If the threshold value is 0, the response is always grounded with Google Search; if it's 1, it never is.

#### How dynamic retrieval works

You can use dynamic retrieval in your request to choose when to turn on Grounding with Google Search. This is useful when the prompt doesn't require an answer grounded in Google Search and the model can provide an answer based on its own knowledge without grounding. This helps you manage latency, quality, and cost more effectively.

Before you invoke the dynamic retrieval configuration in your request, understand the following terminology:

-   **Prediction score**: When you request a grounded answer, Gemini assigns a _prediction score_ to the prompt. The prediction score is a floating point value in the range \[0,1\]. Its value depends on whether the prompt can benefit from grounding the answer with the most up-to-date information from Google Search. Thus, if a prompt requires an answer grounded in the most recent facts on the web, it has a higher prediction score. A prompt for which a model-generated answer is sufficient has a lower prediction score.
    
    Here are examples of some prompts and their prediction scores.
    
    **Note:** The prediction scores are assigned by Gemini and can vary over time depending on several factors.
    
    Prompt
    
    Prediction score
    
    Comment
    
    "Write a poem about peonies"
    
    0.13
    
    The model can rely on its knowledge and the answer doesn't need grounding.
    
    "Suggest a toy for a 2yo child"
    
    0.36
    
    The model can rely on its knowledge and the answer doesn't need grounding.
    
    "Can you give a recipe for an asian-inspired guacamole?"
    
    0.55
    
    Google Search can give a grounded answer, but grounding isn't strictly required; the model knowledge might be sufficient.
    
    "What's Agent Builder? How is grounding billed in Agent Builder?"
    
    0.72
    
    Requires Google Search to generate a well-grounded answer.
    
    "Who won the latest F1 grand prix?"
    
    0.97
    
    Requires Google Search to generate a well-grounded answer.
    
-   **Threshold**: In your API request, you can specify a dynamic retrieval configuration with a threshold. The threshold is a floating point value in the range \[0,1\] and defaults to 0.3. If the threshold value is zero, the response is always grounded with Google Search. For all other values of threshold, the following is applicable:
    
    -   If the prediction score is greater than or equal to the threshold, the answer is grounded with Google Search. A lower threshold implies that more prompts have responses that are generated using Grounding with Google Search.
    -   If the prediction score is less than the threshold, the model might still generate the answer, but it isn't grounded with Google Search.

To learn how to set the dynamic retrieval threshold using an SDK or the REST API, see the appropriate [code example](https://ai.google.dev/gemini-api/docs/grounding?lang=python#configure-grounding).

To find a good threshold that suits your business needs, you can create a representative set of queries that you expect to encounter. Then you can sort the queries according to the prediction score in the response and select a good threshold for your use case.

## A grounded response

If your prompt successfully grounds to Google Search, the response will include `groundingMetadata`. A grounded response might look something like this (parts of the response have been omitted for brevity):

{
      "candidates": [
        {
          "content": {
            "parts": [
              {
                "text": "Carlos Alcaraz won the Gentlemen's Singles title at the 2024 Wimbledon Championships. He defeated Novak Djokovic in the final, winning his second consecutive Wimbledon title and fourth Grand Slam title overall. \n"
              }
            ],
            "role": "model"
          },
          ...
          "groundingMetadata": {
            "searchEntryPoint": {
              "renderedContent": "\u003cstyle\u003e\n.container {\n  align-items: center;\n  border-radius: 8px;\n  display: flex;\n  font-family: Google Sans, Roboto, sans-serif;\n  font-size: 14px;\n  line-height: 20px;\n  padding: 8px 12px;\n}\n.chip {\n  display: inline-block;\n  border: solid 1px;\n  border-radius: 16px;\n  min-width: 14px;\n  padding: 5px 16px;\n  text-align: center;\n  user-select: none;\n  margin: 0 8px;\n  -webkit-tap-highlight-color: transparent;\n}\n.carousel {\n  overflow: auto;\n  scrollbar-width: none;\n  white-space: nowrap;\n  margin-right: -12px;\n}\n.headline {\n  display: flex;\n  margin-right: 4px;\n}\n.gradient-container {\n  position: relative;\n}\n.gradient {\n  position: absolute;\n  transform: translate(3px, -9px);\n  height: 36px;\n  width: 9px;\n}\n@media (prefers-color-scheme: light) {\n  .container {\n    background-color: #fafafa;\n    box-shadow: 0 0 0 1px #0000000f;\n  }\n  .headline-label {\n    color: #1f1f1f;\n  }\n  .chip {\n    background-color: #ffffff;\n    border-color: #d2d2d2;\n    color: #5e5e5e;\n    text-decoration: none;\n  }\n  .chip:hover {\n    background-color: #f2f2f2;\n  }\n  .chip:focus {\n    background-color: #f2f2f2;\n  }\n  .chip:active {\n    background-color: #d8d8d8;\n    border-color: #b6b6b6;\n  }\n  .logo-dark {\n    display: none;\n  }\n  .gradient {\n    background: linear-gradient(90deg, #fafafa 15%, #fafafa00 100%);\n  }\n}\n@media (prefers-color-scheme: dark) {\n  .container {\n    background-color: #1f1f1f;\n    box-shadow: 0 0 0 1px #ffffff26;\n  }\n  .headline-label {\n    color: #fff;\n  }\n  .chip {\n    background-color: #2c2c2c;\n    border-color: #3c4043;\n    color: #fff;\n    text-decoration: none;\n  }\n  .chip:hover {\n    background-color: #353536;\n  }\n  .chip:focus {\n    background-color: #353536;\n  }\n  .chip:active {\n    background-color: #464849;\n    border-color: #53575b;\n  }\n  .logo-light {\n    display: none;\n  }\n  .gradient {\n    background: linear-gradient(90deg, #1f1f1f 15%, #1f1f1f00 100%);\n  }\n}\n\u003c/style\u003e\n\u003cdiv class=\"container\"\u003e\n  \u003cdiv class=\"headline\"\u003e\n    \u003csvg class=\"logo-light\" width=\"18\" height=\"18\" viewBox=\"9 9 35 35\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\"\u003e\n      \u003cpath fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M42.8622 27.0064C42.8622 25.7839 42.7525 24.6084 42.5487 23.4799H26.3109V30.1568H35.5897C35.1821 32.3041 33.9596 34.1222 32.1258 35.3448V39.6864H37.7213C40.9814 36.677 42.8622 32.2571 42.8622 27.0064V27.0064Z\" fill=\"#4285F4\"/\u003e\n      \u003cpath fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M26.3109 43.8555C30.9659 43.8555 34.8687 42.3195 37.7213 39.6863L32.1258 35.3447C30.5898 36.3792 28.6306 37.0061 26.3109 37.0061C21.8282 37.0061 18.0195 33.9811 16.6559 29.906H10.9194V34.3573C13.7563 39.9841 19.5712 43.8555 26.3109 43.8555V43.8555Z\" fill=\"#34A853\"/\u003e\n      \u003cpath fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M16.6559 29.8904C16.3111 28.8559 16.1074 27.7588 16.1074 26.6146C16.1074 25.4704 16.3111 24.3733 16.6559 23.3388V18.8875H10.9194C9.74388 21.2072 9.06992 23.8247 9.06992 26.6146C9.06992 29.4045 9.74388 32.022 10.9194 34.3417L15.3864 30.8621L16.6559 29.8904V29.8904Z\" fill=\"#FBBC05\"/\u003e\n      \u003cpath fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M26.3109 16.2386C28.85 16.2386 31.107 17.1164 32.9095 18.8091L37.8466 13.8719C34.853 11.082 30.9659 9.3736 26.3109 9.3736C19.5712 9.3736 13.7563 13.245 10.9194 18.8875L16.6559 23.3388C18.0195 19.2636 21.8282 16.2386 26.3109 16.2386V16.2386Z\" fill=\"#EA4335\"/\u003e\n    \u003c/svg\u003e\n    \u003csvg class=\"logo-dark\" width=\"18\" height=\"18\" viewBox=\"0 0 48 48\" xmlns=\"http://www.w3.org/2000/svg\"\u003e\n      \u003ccircle cx=\"24\" cy=\"23\" fill=\"#FFF\" r=\"22\"/\u003e\n      \u003cpath d=\"M33.76 34.26c2.75-2.56 4.49-6.37 4.49-11.26 0-.89-.08-1.84-.29-3H24.01v5.99h8.03c-.4 2.02-1.5 3.56-3.07 4.56v.75l3.91 2.97h.88z\" fill=\"#4285F4\"/\u003e\n      \u003cpath d=\"M15.58 25.77A8.845 8.845 0 0 0 24 31.86c1.92 0 3.62-.46 4.97-1.31l4.79 3.71C31.14 36.7 27.65 38 24 38c-5.93 0-11.01-3.4-13.45-8.36l.17-1.01 4.06-2.85h.8z\" fill=\"#34A853\"/\u003e\n      \u003cpath d=\"M15.59 20.21a8.864 8.864 0 0 0 0 5.58l-5.03 3.86c-.98-2-1.53-4.25-1.53-6.64 0-2.39.55-4.64 1.53-6.64l1-.22 3.81 2.98.22 1.08z\" fill=\"#FBBC05\"/\u003e\n      \u003cpath d=\"M24 14.14c2.11 0 4.02.75 5.52 1.98l4.36-4.36C31.22 9.43 27.81 8 24 8c-5.93 0-11.01 3.4-13.45 8.36l5.03 3.85A8.86 8.86 0 0 1 24 14.14z\" fill=\"#EA4335\"/\u003e\n    \u003c/svg\u003e\n    \u003cdiv class=\"gradient-container\"\u003e\u003cdiv class=\"gradient\"\u003e\u003c/div\u003e\u003c/div\u003e\n  \u003c/div\u003e\n  \u003cdiv class=\"carousel\"\u003e\n    \u003ca class=\"chip\" href=\"https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWhgh4x8Epe-gzpwRBvp7o3RZh2m1ygq1EHktn0OWCtvTXjad4bb1zSuqfJd6OEuZZ9_SXZ_P2SvCpJM7NaFfQfiZs6064MeqXego0vSbV9LlAZoxTdbxWK1hFeqTG6kA13YJf7Fbu1SqBYM0cFM4zo0G_sD9NKYWcOCQMvDLDEJFhjrC9DM_QobBIAMq-gWN95G5tvt6_z6EuPN8QY=\"\u003ewho won wimbledon 2024\u003c/a\u003e\n  \u003c/div\u003e\n\u003c/div\u003e\n"
            },
            "groundingChunks": [
              {
                "web": {
                  "uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWhgh4whET1ta3sDETZvcicd8FeNe4z0VuduVsxrT677KQRp2rYghXI0VpfYbIMVI3THcTuMwggRCbFXS_wVvW0UmGzMe9h2fyrkvsnQPJyikJasNIbjJLPX0StM4Bd694-ZVle56MmRA4YiUvwSqad1w6O2opmWnw==",
                  "title": "wikipedia.org"
                }
              },
              {
                "web": {
                  "uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWhgh4wR1M-9-yMPUr_KdHlnoAmQ8ZX90DtQ_vDYTjtP2oR5RH4tRP04uqKPLmesvo64BBkPeYLC2EpVDxv9ngO3S1fs2xh-e78fY4m0GAtgNlahUkm_tBm_sih5kFPc7ill9u2uwesNGUkwrQlmP2mfWNU5lMMr23HGktr6t0sV0QYlzQq7odVoBxYWlQ_sqWFH",
                  "title": "wikipedia.org"
                }
              },
              {
                "web": {
                  "uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWhgh4wsDmROzbP-tmt8GdwCW_pqISTZ4IRbBuoaMyaHfcQg8WW-yKRQQvMDTPAuLxJh-8_U8_iw_6JKFbQ8M9oVYtaFdWFK4gOtL4RrC9Jyqc5BNpuxp6uLEKgL5-9TggtNvO97PyCfziDFXPsxylwI1HcfQdrz3Jy7ZdOL4XM-S5rC0lF2S3VWW0IEAEtS7WX861meBYVjIuuF_mIr3spYPqWLhbAY2Spj-4_ba8DjRvmevIFUhRuESTKvBfmpxNSM",
                  "title": "cbssports.com"
                }
              },
              {
                "web": {
                  "uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWhgh4yzjLkorHiUKjhOPkWaZ9b4cO-cLG-02vlEl6xTBjMUjyhK04qSIclAa7heR41JQ6AAVXmNdS3WDrLOV4Wli-iezyzW8QPQ4vgnmO_egdsuxhcGk3-Fp8-yfqNLvgXFwY5mPo6QRhvplOFv0_x9mAcka18QuAXtj0SPvJfZhUEgYLCtCrucDS5XFc5HmRBcG1tqFdKSE1ihnp8KLdaWMhrUQI21hHS9",
                  "title": "jagranjosh.com"
                }
              },
              {
                "web": {
                  "uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWhgh4y9L4oeNGWCatFz63b9PpP3ys-Wi_zwnkUT5ji9lY7gPUJQcsmmE87q88GSdZqzcx5nZG9usot5FYk2yK-FAGvCRE6JsUQJB_W11_kJU2HVV1BTPiZ4SAgm8XDFIxpCZXnXmEx5HUfRqQm_zav7CvS2qjA2x3__qLME6Jy7R5oza1C5_aqjQu422le9CaigThS5bvJoMo-ZGcXdBUCj2CqoXNVjMA==",
                  "title": "apnews.com"
                }
              }
            ],
            "groundingSupports": [
              {
                "segment": {
                  "endIndex": 85,
                  "text": "Carlos Alcaraz won the Gentlemen's Singles title at the 2024 Wimbledon Championships."
                },
                "groundingChunkIndices": [
                  0,
                  1,
                  2,
                  3
                ],
                "confidenceScores": [
                  0.97380733,
                  0.97380733,
                  0.97380733,
                  0.97380733
                ]
              },
              {
                "segment": {
                  "startIndex": 86,
                  "endIndex": 210,
                  "text": "He defeated Novak Djokovic in the final, winning his second consecutive Wimbledon title and fourth Grand Slam title overall."
                },
                "groundingChunkIndices": [
                  1,
                  0,
                  4
                ],
                "confidenceScores": [
                  0.96145374,
                  0.96145374,
                  0.96145374
                ]
              }
            ],
            "webSearchQueries": [
              "who won wimbledon 2024"
            ]
          }
        }
      ],
      ...
    }

If the response doesn't include `groundingMetadata`, this means the response wasn't successfully grounded. There are several reasons this could happen, including low source relevance or incomplete information within the model response.

When a grounded result is generated, the metadata contains URIs that redirect to the publishers of the content that was used to generate the grounded result. These URIs contain the `vertexaisearch` subdomain, as in this truncated example: `https://vertexaisearch.cloud.google.com/grounding-api-redirect/...`. The metadata also contains the publishers' domains. The provided URIs remain accessible for 30 days after the grounded result is generated.

**Important:** The provided URIs must be directly accessible by the end users and must not be queried programmatically through automated means. If automated access is detected, the grounded answer generation service might stop providing the redirection URIs.

The `renderedContent` field within `searchEntryPoint` is the provided code for implementing Google Search Suggestions. See [Use Google Search Suggestions](https://ai.google.dev/gemini-api/docs/grounding/search-suggestions) to learn more.

# Troubleshooting guide

-   On this page
-   [Gemini API backend service error codes](https://ai.google.dev/gemini-api/docs/troubleshooting?lang=python#error-codes)
-   [Client SDK error codes](https://ai.google.dev/gemini-api/docs/troubleshooting?lang=python#client-sdk-error-codes)
-   [Check your API calls for model parameter errors](https://ai.google.dev/gemini-api/docs/troubleshooting?lang=python#check-api)
-   [Check if you have the right model](https://ai.google.dev/gemini-api/docs/troubleshooting?lang=python#check-if)
-   [Safety issues](https://ai.google.dev/gemini-api/docs/troubleshooting?lang=python#safety-issues)
-   [Recitation issue](https://ai.google.dev/gemini-api/docs/troubleshooting?lang=python#recitation-issue)
-   [Improve model output](https://ai.google.dev/gemini-api/docs/troubleshooting?lang=python#improve-model)
-   [Understand token limits](https://ai.google.dev/gemini-api/docs/troubleshooting?lang=python#understand-token)
-   [Known issues](https://ai.google.dev/gemini-api/docs/troubleshooting?lang=python#known-issues)
-   [File a bug](https://ai.google.dev/gemini-api/docs/troubleshooting?lang=python#file-bug)

Python Go

Use this guide to help you diagnose and resolve common issues that arise when you call the Gemini API. You may encounter issues from either the Gemini API backend service or the client SDKs. Our client SDKs are open sourced in the following repositories:

-   [python-genai](https://github.com/googleapis/python-genai)
-   [generative-ai-js](https://github.com/google-gemini/generative-ai-js)
-   [generative-ai-go](https://github.com/google/generative-ai-go)

If you encounter API key issues, ensure you have set up your API key correctly per the [API key setup guide](https://ai.google.dev/tutorials/setup).

## Gemini API backend service error codes

The following table lists common backend error codes you may encounter, along with explanations for their causes and troubleshooting steps:

**HTTP Code**

**Status**

**Description**

**Example**

**Solution**

400

INVALID\_ARGUMENT

The request body is malformed.

There is a typo, or a missing required field in your request.

Check the [API reference](https://ai.google.dev/api) for request format, examples, and supported versions. Using features from a newer API version with an older endpoint can cause errors.

400

FAILED\_PRECONDITION

Gemini API free tier is not available in your country. Please enable billing on your project in Google AI Studio.

You are making a request in a region where the free tier is not supported, and you have not enabled billing on your project in Google AI Studio.

To use the Gemini API, you will need to setup a paid plan using [Google AI Studio](https://aistudio.google.com/app/plan_information).

403

PERMISSION\_DENIED

Your API key doesn't have the required permissions.

You are using the wrong API key; you are trying to use a tuned model without going through [proper authentication](https://ai.google.dev/docs/model-tuning/tutorial?lang=python#set_up_authentication).

Check that your API key is set and has the right access. And make sure to go through proper authentication to use tuned models.

404

NOT\_FOUND

The requested resource wasn't found.

An image, audio, or video file referenced in your request was not found.

Check if all [parameters in your request are valid](https://ai.google.dev/docs/troubleshooting#check-api) for your API version.

429

RESOURCE\_EXHAUSTED

You've exceeded the rate limit.

You are sending too many requests per minute with the free tier Gemini API.

Ensure you're within the model's [rate limit](https://ai.google.dev/models/gemini#model-variations). [Request a quota increase](https://ai.google.dev/docs/increase_quota) if needed.

500

INTERNAL

An unexpected error occurred on Google's side.

Your input context is too long.

Reduce your input context or temporarily switch to another model (e.g. from Gemini 1.5 Pro to Gemini 1.5 Flash) and see if it works. Or wait a bit and retry your request. If the issue persists after retrying, please report it using the **Send feedback** button in Google AI Studio.

503

UNAVAILABLE

The service may be temporarily overloaded or down.

The service is temporarily running out of capacity.

Temporarily switch to another model (e.g. from Gemini 1.5 Pro to Gemini 1.5 Flash) and see if it works. Or wait a bit and retry your request. If the issue persists after retrying, please report it using the **Send feedback** button in Google AI Studio.

504

DEADLINE\_EXCEEDED

The service is unable to finish processing within the deadline.

Your prompt (or context) is too large to be processed in time.

Set a larger 'timeout' in your client request to avoid this error.

## Client SDK error codes

The following table lists common [Python client SDK](https://github.com/googleapis/python-genai) error codes you may encounter, along with explanations for their causes:

Exception/Error Type

Class

Description

APIError

google.genai.errors.APIError

General errors raised by the GenAI API.

ClientError

google.genai.errors.ClientError

Client error raised by the GenAI API.

ServerError

google.genai.errors.ServerError

Server error raised by the GenAI API.

UnknownFunctionCallArgumentError

google.genai.errors.UnknownFunctionCallArgumentError

Raised when the function call argument cannot be converted to the parameter annotation.

UnsupportedFunctionError

google.genai.errors.UnsupportedFunctionError

Raised when the function is not supported.

FunctionInvocationError

google.genai.errors.FunctionInvocationError

Raised when the function cannot be invoked with the given arguments.

ValidationError

pydantic.ValidationError

Raised by [Pydantic](https://docs.pydantic.dev/latest/api/pydantic_core/#pydantic_core.ValidationError) whenever it finds an error in the data it's validating. See [Pydantic error handling](https://docs.pydantic.dev/latest/errors/errors/).

You'll also find all errors in the [errors class](https://github.com/googleapis/python-genai/blob/main/google/genai/errors.py).

To handle errors raised by the SDK, you can use a `try-except` block:

from google.genai import errors
    
    try:
        client.models.generate_content(
            model="invalid-model-name",
            contents="What is your name?",
        )
    except errors.APIError as e:
        print(e.code) # 404
        print(e.message)

## Check your API calls for model parameter errors

Ensure your model parameters are within the following values:

**Model parameter**

**Values (range)**

Candidate count

1-8 (integer)

Temperature

0.0-1.0

Max output tokens

Use `get_model` ([Python](https://ai.google.dev/api/python/google/generativeai/get_model)) to determine the maximum number of tokens for the model you are using.

TopP

0.0-1.0

In addition to checking parameter values, make sure you're using the correct [API version](https://ai.google.dev/gemini-api/docs/api-versions) (e.g., `/v1` or `/v1beta`) and model that supports the features you need. For example, if a feature is in Beta release, it will only be available in the `/v1beta` API version.

## Check if you have the right model

Ensure you are using a supported model listed on our [models page](https://ai.google.dev/gemini-api/docs/models/gemini).

## Safety issues

If you see a prompt was blocked because of a safety setting in your API call, review the prompt with respect to the filters you set in the API call.

If you see `BlockedReason.OTHER`, the query or response may violate the [terms of service](https://ai.google.dev/terms) or be otherwise unsupported.

## Recitation issue

If you see the model stops generating output due to the RECITATION reason, this means the model output may resemble certain data. To fix this, try to make prompt / context as unique as possible and use a higher temperature.

## Improve model output

For higher quality model outputs, explore writing more structured prompts. The [introduction to prompt design](https://ai.google.dev/docs/prompt_best_practices) page introduces some basic concepts, strategies, and best practices to get you started.

If you have hundreds of examples of good input/output pairs, you can also consider [model tuning](https://ai.google.dev/docs/model_tuning_guidance).

## Understand token limits

Read through our [Token guide](https://ai.google.dev/gemini-api/docs/tokens) to better understand how to count tokens and their limits.

## Known issues

-   The API supports only a number of select languages. Submitting prompts in unsupported languages can produce unexpected or even blocked responses. See [available languages](https://ai.google.dev/models/gemini#available-languages) for updates.

## File a bug

Join the discussion on the [Google AI developer forum](https://discuss.ai.google.dev/) if you have questions.

# OpenAI compatibility

-   On this page
-   [List models](https://ai.google.dev/gemini-api/docs/openai#list-models)
-   [Retrieve a model](https://ai.google.dev/gemini-api/docs/openai#retrieve-model)
-   [Streaming](https://ai.google.dev/gemini-api/docs/openai#streaming)
-   [Function calling](https://ai.google.dev/gemini-api/docs/openai#function-calling)
-   [Image understanding](https://ai.google.dev/gemini-api/docs/openai#image-understanding)
-   [Generate an image](https://ai.google.dev/gemini-api/docs/openai#generate-image)
-   [Audio understanding](https://ai.google.dev/gemini-api/docs/openai#audio-understanding)
-   [Structured output](https://ai.google.dev/gemini-api/docs/openai#structured-output)
-   [Embeddings](https://ai.google.dev/gemini-api/docs/openai#embeddings)
-   [Current limitations](https://ai.google.dev/gemini-api/docs/openai#current-limitations)

Gemini models are accessible using the OpenAI libraries (Python and TypeScript / Javascript) along with the REST API, by updating three lines of code and using your [Gemini API key](https://aistudio.google.com/apikey). If you aren't already using the OpenAI libraries, we recommend that you call the [Gemini API directly](https://ai.google.dev/gemini-api/docs/quickstart).

[Python](https://ai.google.dev/gemini-api/docs/openai#python)[Node.js](https://ai.google.dev/gemini-api/docs/openai#node.js)[REST](https://ai.google.dev/gemini-api/docs/openai#rest) More

from openai import OpenAI
    
    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    response = client.chat.completions.create(
        model="gemini-2.0-flash",
        n=1,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": "Explain to me how AI works"
            }
        ]
    )
    
    print(response.choices[0].message)

import OpenAI from "openai";
    
    const openai = new OpenAI({
        apiKey: "GEMINI_API_KEY",
        baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/"
    });
    
    const response = await openai.chat.completions.create({
        model: "gemini-2.0-flash",
        messages: [
            { role: "system", content: "You are a helpful assistant." },
            {
                role: "user",
                content: "Explain to me how AI works",
            },
        ],
    });
    
    console.log(response.choices[0].message);

curl "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer GEMINI_API_KEY" \
    -d '{
        "model": "gemini-2.0-flash",
        "messages": [
            {"role": "user", "content": "Explain to me how AI works"}
        ]
        }'

What changed? Just three lines!

-   **`api_key="GEMINI_API_KEY"`**: Simply replace "`GEMINI_API_KEY`" with your actual Gemini API key, which you can get in [Google AI Studio](https://aistudio.google.com/).
    
-   **`base_url="https://generativelanguage.googleapis.com/v1beta/openai/"`:** This tells the OpenAI library to send requests to the Gemini API endpoint instead of the standard OpenAI one.
    
-   **`model="gemini-2.0-flash"`**: We're specifying the powerful and efficient gemini-2.0-flash model.
    

## List models

Get a list of available Gemini models:

[Python](https://ai.google.dev/gemini-api/docs/openai#python)[Node.js](https://ai.google.dev/gemini-api/docs/openai#node.js)[REST](https://ai.google.dev/gemini-api/docs/openai#rest) More

from openai import OpenAI
    
    client = OpenAI(
      api_key="GEMINI_API_KEY",
      base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    models = client.models.list()
    for model in models:
      print(model.id)

import OpenAI from "openai";
    
    const openai = new OpenAI({
      apiKey: "GEMINI_API_KEY",
      baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/",
    });
    
    async function main() {
      const list = await openai.models.list();
    
      for await (const model of list) {
        console.log(model);
      }
    }
    main();

curl https://generativelanguage.googleapis.com/v1beta/openai/models \
    -H "Authorization: Bearer GEMINI_API_KEY"

## Retrieve a model

Retrieve a Gemini model:

[Python](https://ai.google.dev/gemini-api/docs/openai#python)[Node.js](https://ai.google.dev/gemini-api/docs/openai#node.js)[REST](https://ai.google.dev/gemini-api/docs/openai#rest) More

from openai import OpenAI
    
    client = OpenAI(
      api_key="GEMINI_API_KEY",
      base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    model = client.models.retrieve("gemini-2.0-flash")
    print(model.id)

import OpenAI from "openai";
    
    const openai = new OpenAI({
      apiKey: "GEMINI_API_KEY",
      baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/",
    });
    
    async function main() {
      const model = await openai.models.retrieve("gemini-2.0-flash");
      console.log(model.id);
    }
    
    main();

curl https://generativelanguage.googleapis.com/v1beta/openai/models/gemini-2.0-flash \
    -H "Authorization: Bearer GEMINI_API_KEY"

## Streaming

The Gemini API supports [streaming responses](https://ai.google.dev/gemini-api/docs/text-generation?lang=python#generate-a-text-stream).

[Python](https://ai.google.dev/gemini-api/docs/openai#python)[Node.js](https://ai.google.dev/gemini-api/docs/openai#node.js)[REST](https://ai.google.dev/gemini-api/docs/openai#rest) More

from openai import OpenAI
    
    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    response = client.chat.completions.create(
      model="gemini-2.0-flash",
      messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
      ],
      stream=True
    )
    
    for chunk in response:
        print(chunk.choices[0].delta)

import OpenAI from "openai";
    
    const openai = new OpenAI({
        apiKey: "GEMINI_API_KEY",
        baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/"
    });
    
    async function main() {
      const completion = await openai.chat.completions.create({
        model: "gemini-2.0-flash",
        messages: [
          {"role": "system", "content": "You are a helpful assistant."},
          {"role": "user", "content": "Hello!"}
        ],
        stream: true,
      });
    
      for await (const chunk of completion) {
        console.log(chunk.choices[0].delta.content);
      }
    }
    
    main();

curl "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer GEMINI_API_KEY" \
    -d '{
        "model": "gemini-2.0-flash",
        "messages": [
            {"role": "user", "content": "Explain to me how AI works"}
        ],
        "stream": true
      }'

## Function calling

Function calling makes it easier for you to get structured data outputs from generative models and is [supported in the Gemini API](https://ai.google.dev/gemini-api/docs/function-calling/tutorial).

[Python](https://ai.google.dev/gemini-api/docs/openai#python)[Node.js](https://ai.google.dev/gemini-api/docs/openai#node.js)[REST](https://ai.google.dev/gemini-api/docs/openai#rest) More

from openai import OpenAI
    
    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    tools = [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "description": "Get the weather in a given location",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {
                "type": "string",
                "description": "The city and state, e.g. Chicago, IL",
              },
              "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["location"],
          },
        }
      }
    ]
    
    messages = [{"role": "user", "content": "What's the weather like in Chicago today?"}]
    response = client.chat.completions.create(
      model="gemini-2.0-flash",
      messages=messages,
      tools=tools,
      tool_choice="auto"
    )
    
    print(response)

import OpenAI from "openai";
    
    const openai = new OpenAI({
        apiKey: "GEMINI_API_KEY",
        baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/"
    });
    
    async function main() {
      const messages = [{"role": "user", "content": "What's the weather like in Chicago today?"}];
      const tools = [
          {
            "type": "function",
            "function": {
              "name": "get_weather",
              "description": "Get the weather in a given location",
              "parameters": {
                "type": "object",
                "properties": {
                  "location": {
                    "type": "string",
                    "description": "The city and state, e.g. Chicago, IL",
                  },
                  "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
              },
            }
          }
      ];
    
      const response = await openai.chat.completions.create({
        model: "gemini-2.0-flash",
        messages: messages,
        tools: tools,
        tool_choice: "auto",
      });
    
      console.log(response);
    }
    
    main();

curl "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer GEMINI_API_KEY" \
    -d '{
      "model": "gemini-2.0-flash",
      "messages": [
        {
          "role": "user",
          "content": "What'\''s the weather like in Chicago today?"
        }
      ],
      "tools": [
        {
          "type": "function",
          "function": {
            "name": "get_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
              "type": "object",
              "properties": {
                "location": {
                  "type": "string",
                  "description": "The city and state, e.g. Chicago, IL"
                },
                "unit": {
                  "type": "string",
                  "enum": ["celsius", "fahrenheit"]
                }
              },
              "required": ["location"]
            }
          }
        }
      ],
      "tool_choice": "auto"
    }'

## Image understanding

Gemini models are natively multimodal and provide best in class performance on [many common vision tasks](https://ai.google.dev/gemini-api/docs/vision).

[Python](https://ai.google.dev/gemini-api/docs/openai#python)[Node.js](https://ai.google.dev/gemini-api/docs/openai#node.js)[REST](https://ai.google.dev/gemini-api/docs/openai#rest) More

import base64
    from openai import OpenAI
    
    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    # Function to encode the image
    def encode_image(image_path):
      with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
    # Getting the base64 string
    base64_image = encode_image("Path/to/agi/image.jpeg")
    
    response = client.chat.completions.create(
      model="gemini-2.0-flash",
      messages=[
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": "What is in this image?",
            },
            {
              "type": "image_url",
              "image_url": {
                "url":  f"data:image/jpeg;base64,{base64_image}"
              },
            },
          ],
        }
      ],
    )
    
    print(response.choices[0])

import OpenAI from "openai";
    import fs from 'fs/promises';
    
    const openai = new OpenAI({
      apiKey: "GEMINI_API_KEY",
      baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/"
    });
    
    async function encodeImage(imagePath) {
      try {
        const imageBuffer = await fs.readFile(imagePath);
        return imageBuffer.toString('base64');
      } catch (error) {
        console.error("Error encoding image:", error);
        return null;
      }
    }
    
    async function main() {
      const imagePath = "Path/to/agi/image.jpeg";
      const base64Image = await encodeImage(imagePath);
    
      const messages = [
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": "What is in this image?",
            },
            {
              "type": "image_url",
              "image_url": {
                "url": `data:image/jpeg;base64,${base64Image}`
              },
            },
          ],
        }
      ];
    
      try {
        const response = await openai.chat.completions.create({
          model: "gemini-2.0-flash",
          messages: messages,
        });
    
        console.log(response.choices[0]);
      } catch (error) {
        console.error("Error calling Gemini API:", error);
      }
    }
    
    main();

bash -c '
      base64_image=$(base64 -i "Path/to/agi/image.jpeg");
      curl "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer GEMINI_API_KEY" \
        -d "{
          \"model\": \"gemini-2.0-flash\",
          \"messages\": [
            {
              \"role\": \"user\",
              \"content\": [
                { \"type\": \"text\", \"text\": \"What is in this image?\" },
                {
                  \"type\": \"image_url\",
                  \"image_url\": { \"url\": \"data:image/jpeg;base64,${base64_image}\" }
                }
              ]
            }
          ]
        }"
    '

## Generate an image

**Note:** Image generation is only available in the paid tier.

Generate an image:

[Python](https://ai.google.dev/gemini-api/docs/openai#python)[Node.js](https://ai.google.dev/gemini-api/docs/openai#node.js)[REST](https://ai.google.dev/gemini-api/docs/openai#rest) More

import base64
    from openai import OpenAI
    from PIL import Image
    from io import BytesIO
    
    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    
    response = client.images.generate(
        model="imagen-3.0-generate-002",
        prompt="a portrait of a sheepadoodle wearing a cape",
        response_format='b64_json',
        n=1,
    )
    
    for image_data in response.data:
      image = Image.open(BytesIO(base64.b64decode(image_data.b64_json)))
      image.show()

import OpenAI from "openai";
    
    const openai = new OpenAI({
      apiKey: "GEMINI_API_KEY",
      baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/",
    });
    
    async function main() {
      const image = await openai.images.generate(
        {
          model: "imagen-3.0-generate-002",
          prompt: "a portrait of a sheepadoodle wearing a cape",
          response_format: "b64_json",
          n: 1,
        }
      );
    
      console.log(image.data);
    }
    
    main();

curl "https://generativelanguage.googleapis.com/v1beta/openai/images/generations" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer GEMINI_API_KEY" \
      -d '{
            "model": "imagen-3.0-generate-002",
            "prompt": "a portrait of a sheepadoodle wearing a cape",
            "response_format": "b64_json",
            "n": 1,
          }'

## Audio understanding

Analyze audio input:

[Python](https://ai.google.dev/gemini-api/docs/openai#python)[Node.js](https://ai.google.dev/gemini-api/docs/openai#node.js)[REST](https://ai.google.dev/gemini-api/docs/openai#rest) More

import base64
    from openai import OpenAI
    
    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    with open("/path/to/your/audio/file.wav", "rb") as audio_file:
      base64_audio = base64.b64encode(audio_file.read()).decode('utf-8')
    
    response = client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": "Transcribe this audio",
            },
            {
                  "type": "input_audio",
                  "input_audio": {
                    "data": base64_audio,
                    "format": "wav"
              }
            }
          ],
        }
      ],
    )
    
    print(response.choices[0].message.content)

import fs from "fs";
    import OpenAI from "openai";
    
    const client = new OpenAI({
      apiKey: "GEMINI_API_KEY",
      baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/",
    });
    
    const audioFile = fs.readFileSync("/path/to/your/audio/file.wav");
    const base64Audio = Buffer.from(audioFile).toString("base64");
    
    async function main() {
      const response = await client.chat.completions.create({
        model: "gemini-2.0-flash",
        messages: [
          {
            role: "user",
            content: [
              {
                type: "text",
                text: "Transcribe this audio",
              },
              {
                type: "input_audio",
                input_audio: {
                  data: base64Audio,
                  format: "wav",
                },
              },
            ],
          },
        ],
      });
    
      console.log(response.choices[0].message.content);
    }
    
    main();

**Note:** If you get an `Argument list too long` error, the encoding of your audio file might be too long for curl.

bash -c '
      base64_audio=$(base64 -i "/path/to/your/audio/file.wav");
      curl "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer GEMINI_API_KEY" \
        -d "{
          \"model\": \"gemini-2.0-flash\",
          \"messages\": [
            {
              \"role\": \"user\",
              \"content\": [
                { \"type\": \"text\", \"text\": \"Transcribe this audio file.\" },
                {
                  \"type\": \"input_audio\",
                  \"input_audio\": {
                    \"data\": \"${base64_audio}\",
                    \"format\": \"wav\"
                  }
                }
              ]
            }
          ]
        }"
    '

## Structured output

Gemini models can output JSON objects in any [structure you define](https://ai.google.dev/gemini-api/docs/structured-output).

[Python](https://ai.google.dev/gemini-api/docs/openai#python)[Node.js](https://ai.google.dev/gemini-api/docs/openai#node.js) More

from pydantic import BaseModel
    from openai import OpenAI
    
    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    class CalendarEvent(BaseModel):
        name: str
        date: str
        participants: list[str]
    
    completion = client.beta.chat.completions.parse(
        model="gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "Extract the event information."},
            {"role": "user", "content": "John and Susan are going to an AI conference on Friday."},
        ],
        response_format=CalendarEvent,
    )
    
    print(completion.choices[0].message.parsed)

import OpenAI from "openai";
    import { zodResponseFormat } from "openai/helpers/zod";
    import { z } from "zod";
    
    const openai = new OpenAI({
        apiKey: "GEMINI_API_KEY",
        baseURL: "https://generativelanguage.googleapis.com/v1beta/openai"
    });
    
    const CalendarEvent = z.object({
      name: z.string(),
      date: z.string(),
      participants: z.array(z.string()),
    });
    
    const completion = await openai.beta.chat.completions.parse({
      model: "gemini-2.0-flash",
      messages: [
        { role: "system", content: "Extract the event information." },
        { role: "user", content: "John and Susan are going to an AI conference on Friday" },
      ],
      response_format: zodResponseFormat(CalendarEvent, "event"),
    });
    
    const event = completion.choices[0].message.parsed;
    console.log(event);

## Embeddings

Text embeddings measure the relatedness of text strings and can be generated using the [Gemini API](https://ai.google.dev/gemini-api/docs/embeddings).

[Python](https://ai.google.dev/gemini-api/docs/openai#python)[Node.js](https://ai.google.dev/gemini-api/docs/openai#node.js)[REST](https://ai.google.dev/gemini-api/docs/openai#rest) More

from openai import OpenAI
    
    client = OpenAI(
        api_key="GEMINI_API_KEY",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    response = client.embeddings.create(
        input="Your text string goes here",
        model="text-embedding-004"
    )
    
    print(response.data[0].embedding)

import OpenAI from "openai";
    
    const openai = new OpenAI({
        apiKey: "GEMINI_API_KEY",
        baseURL: "https://generativelanguage.googleapis.com/v1beta/openai/"
    });
    
    async function main() {
      const embedding = await openai.embeddings.create({
        model: "text-embedding-004",
        input: "Your text string goes here",
      });
    
      console.log(embedding);
    }
    
    main();

curl "https://generativelanguage.googleapis.com/v1beta/openai/embeddings" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer GEMINI_API_KEY" \
    -d '{
        "input": "Your text string goes here",
        "model": "text-embedding-004"
      }'

## Current limitations

Support for the OpenAI libraries is still in beta while we extend feature support.

If you have questions about supported parameters, upcoming features, or run into any issues getting started with Gemini, join our [Developer Forum](https://discuss.ai.google.dev/c/gemini-api/4).

Was this helpful?
