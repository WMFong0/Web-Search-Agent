import os
from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException
from openai import OpenAI
from typing import Optional
import uvicorn

load_dotenv()

app = FastAPI()

prompt = """Help the user identify products related to a given abbreviation or term available in Mannings HK or SaSa HK retail store. Return the top results in the format specified.

# Steps
1. Review the user query and focus on identifying products referenced by the term or abbreviation they provide (e.g., "BOH").
2. Cross-reference the provided term against a hypothetical database or knowledge base of health and beauty products available at Mannings HK or SaSa HK.
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

# Endpoint accepting query parameter
@app.post("/input/")
async def post_input(text: Optional[str] = Query(None, description="Text query as query parameter")):
    """Accept query parameters, send to OpenAI Responses API, and return the model's response."""
    
    # Check if text was provided
    if not text:
        raise HTTPException(
            status_code=400, 
            detail="No text provided. Please provide 'text' as a query parameter (e.g., ?text=BOH)"
        )
    
    print("Received input:", text)
    
    try:
        # Set up OpenAI client with Responses API endpoint
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment_name = "Michael-Web-Search-Test"  # Your deployment name
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        
        if not api_key:
            raise HTTPException(
                status_code=500, 
                detail="Azure OpenAI API key not configured. Please check environment variables."
            )
        
        client = OpenAI(
            base_url=endpoint,
            api_key=api_key
        )
        
        # Call OpenAI Responses API
        try:
            completion = client.responses.create(
                model=deployment_name,
                tools=[
                    {
                        "type": "web_search_preview",
                        "user_location": {
                            "type": "approximate",
                            "country": "HK"
                        }
                    }
                ],
                input=prompt + text,
                timeout=30
            )
            
            # Extract the response text
            output = completion.output_text if hasattr(completion, 'output_text') else None

        except Exception as e:
            print(f"OpenAI API call failed: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"OpenAI service error: {str(e)}"
            )
        
        if not output:
            raise HTTPException(
                status_code=500,
                detail="Empty response from OpenAI"
            )
        
        # Format the response
        formatted_output = format_response(output)
        
        return {
            "status": "ok", 
            "input": text, 
            "output": formatted_output if formatted_output else "null"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch any other unexpected errors
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

def format_response(response):
    """Format the output response"""
    try:
        # Format the output response
        response = response.replace("\n", "").strip()
        
        # Check if response is empty after cleaning
        if not response:
            return None
        
        response_list = response.split(",")
        response_list = [item.strip() for item in response_list if item.strip()]
        
        # Return the top result
        return response_list[0] if response_list else None
    
    except Exception as e:
        print(f"Error formatting response: {str(e)}")
        return None

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=True
    )