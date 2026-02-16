import os
from dotenv import load_dotenv

from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI

load_dotenv()


class InputPayload(BaseModel):
    text: str


app = FastAPI()

prompt = """Help the user identify products related to a given abbreviation or term available in Mannings HK or SaSa HK retail store. Return the top results in the format specified.

# Steps
1. Review the user query and focus on identifying products referenced by the term or abbreviation they provide (e.g., "BOH").
2. Cross-reference the provided term against a hypothetical database or knowledge base of health and beauty products available at Mannings HK.
3. Select and return the top results that match the term, with clarity and relevance being prioritized.
4. Format the response in the structure requested by the user (e.g., `product1, product2, product3`).

# Output Format
- Return the list of products as a CSV (Comma-Separated Value) string with no additional text or formatting.
- Example format for the output: `product1, product2, product3`

# Examples
**Input:**
"BOH"

**Repharsed Input**
Hi. I'm a Hong Kong customer looking forward to buy health and beauty products that are available in Mannings HK or SaSa HK retail store. Can you tell what products does "BOH" refer to? Give out the top result in the csv file format: product1, product2, product3.
**Output:**
BOH Bee Honey Mask, BOH Green Tea Essence, BOH Probiotic Lotion

User query: """

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/input")
async def post_input(payload: InputPayload):
    """Accept JSON POSTs like {"text": "..."}, send to OpenAI, and return the model's response."""
    text = payload.text
    print("Received input:", text)

    # Set up OpenAI client
    client = OpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        base_url="https://git-openai-poc.openai.azure.com/",
    )

    # Call OpenAI API
    response = client.chat.completions.create(
        model="gpt-4.1",  # Replace with your deployment name if needed
        messages=[{"role": "user", "content": text}],
        tools=[
            {
                "type": "web_search_preview",
                "user_location": {
                    "type": "approximate",
                    "country": "HK"
                }
            }
        ],
        input= prompt + text
    )

    # Extract the model's reply
    output = response.choices[0].message.content if response.choices else None
    output = format_response(output)
    return {"status": "ok", "input": text, "output": output}

def format_response(response):
    
    # Format the output response
    response = response.replace("\n", "").strip()

    response_list = response.split(",")
    response_list = [item.strip() for item in response_list]
    

    # Implement any necessary formatting logic here
    return response_list[0] if response_list else None # Return the top result

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
