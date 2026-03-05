import logging
from google import genai
from google.genai import types
from src.config import settings

# Initialize the Gemini client (new SDK)
client = genai.Client(api_key=settings.gemini_api_key)

MODEL_NAME = "gemini-2.0-flash-001"

GENERATION_CONFIG = types.GenerateContentConfig(
    temperature=0.4,
    top_p=1,
    top_k=32,
    max_output_tokens=4096,
    safety_settings=[
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_MEDIUM_AND_ABOVE"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    ]
)

def get_template_prompt(template_type: str) -> str:
    """Returns a specific prompt part based on the chosen template."""
    if template_type == "api-first":
        return """
- Focus heavily on API-specific checks: status codes (200, 201, 400, 401, 403, 404, 500), request/response body validation, headers, and authentication.
- Assertions should be specific (e.g., "response body contains 'user_id'").
- Add negative cases for invalid input data types and structures.
"""
    elif template_type == "banking":
        return """
- Add checks for transaction limits, currency validation, balance updates, and commission calculations.
- Include checks for idempotency (e.g., preventing double transactions).
- Add security checks for fraud detection patterns and timeout scenarios.
- Verify that critical actions are logged for audit.
"""
    elif template_type == "ui-automation":
        return """
- Focus on user interactions: clicks, input, navigation, and form submissions.
- Emphasize element locators (CSS selectors, XPaths) for clarity.
- Include visual validation considerations if applicable (e.g., "element X is visible").
- Cover different browser/device scenarios if the context implies it.
- Assertions should focus on the visible state of the UI and user experience.
"""
    elif template_type == "performance":
        return """
- Focus on load, stress, and scalability testing scenarios.
- Include key performance indicators (KPIs) like response time, throughput (TPS), error rate, and resource utilization.
- Suggest scenarios for peak load, sustained load, and breaking point analysis.
- Mention relevant tools or methods where appropriate (e.g., "simulate 100 concurrent users for 5 minutes", "monitor CPU/memory usage").
- Assertions should define acceptable performance thresholds.
"""
    else: # classic
        return """
- Generate a balanced mix of positive, negative, and boundary value cases.
- Cover UI interactions, user roles/permissions, and data validation.
- Ensure Expected Results are clear, concise, and measurable.
"""

def get_base_prompt(output_format: str, template_type: str, history: list = None) -> str:
    """Constructs the main instruction prompt for the LLM."""
    
    format_instructions = {
        "markdown": """
Respond in Markdown format. Use tables for clarity where appropriate.
The final output must be a single markdown text.
Example of a single test case:
**Title:** Successful User Registration
**Priority:** High
**Type:** Positive
**Preconditions:**
1. User is on the registration page.
2. User has a unique and valid email.
**Steps:**
1. Fill in the 'email' field with 'test@example.com'.
2. Fill in the 'password' field with 'Password123'.
3. Click the 'Register' button.
**Expected Result:**
- User is redirected to the dashboard.
- A "Welcome" message is displayed.
- A new user record is created in the database.
""",
        "json": """
Respond with a single, valid JSON object. The root of the object should be a key named "test_cases" which contains an array of test case objects.
Do not include any text or markdown before or after the JSON object.
Each test case object in the array must have the following fields: "title", "priority", "type", "preconditions", "steps", "expected_result".
Example:
{
  "test_cases": [
    {
      "title": "Successful User Registration",
      "priority": "High",
      "type": "Positive",
      "preconditions": [
        "User is on the registration page.",
        "User has a unique and valid email."
      ],
      "steps": [
        "Fill in the 'email' field with 'test@example.com'.",
        "Fill in the 'password' field with 'Password123'.",
        "Click the 'Register' button."
      ],
      "expected_result": [
        "User is redirected to the dashboard.",
        "A 'Welcome' message is displayed.",
        "A new user record is created in the database."
      ]
    }
  ]
}
""",
        "csv": """
Respond in CSV format with a header row. The fields must be: "Title", "Priority", "Type", "Preconditions", "Steps", "Expected Result".
Use double quotes to enclose fields. If a field contains a newline, represent it within the quotes.
Example:
"Title","Priority","Type","Preconditions","Steps","Expected Result"
"Successful User Registration","High","Positive","1. User is on the registration page.
2. User has a unique and valid email.","1. Fill in the 'email' field with 'test@example.com'.
2. Fill in the 'password' field with 'Password123'.
3. Click the 'Register' button."," - User is redirected to the dashboard.
 - A 'Welcome' message is displayed."
"""
    }

    history_prompt = ""
    if history:
        history_prompt = "**Previous conversation history (for context):**\n"
        for entry in history:
            history_prompt += f"User's request:\n---\n{entry.request}\n---\n"
            history_prompt += f"Your generated test cases:\n---\n{entry.response}\n---\n\n"

    prompt = f"""
You are an expert QA architect. Your task is to convert a raw text description of a feature into a structured set of test cases.

{history_prompt}

**Output Format:**
{format_instructions.get(output_format, format_instructions['markdown'])}

**Generation Guidelines ({template_type} template):**
- Create a comprehensive set of at least 5-10 test cases, including Positive, Negative, and Boundary checks.
- If the text mentions API endpoints (e.g., POST /users), generate specific API test cases.
- If the text contains business rules (e.g., "if/then", limits, roles), create test cases to verify them.
- Make the "Expected Result" for each test case concrete and verifiable.
{get_template_prompt(template_type)}

Now, analyze the following raw text and generate the test cases.

**Raw Text:**
"""
    return prompt


def get_critic_prompt(original_text: str, generated_cases: str, output_format: str) -> str:
    """Constructs the prompt for the critic pass."""
    return f"""
You are a world-class QA architect acting as a critic.
Your task is to review a set of auto-generated test cases and improve them.

**Original Requirement Text:**
---
{original_text}
---

**Generated Test Cases ({output_format}):**
---
{generated_cases}
---

**Your Task:**
1.  **Review the generated test cases for quality.** Look for gaps, inaccuracies, or unclear steps. Are there missing negative cases? Are the boundary cases sufficient? Are the expected results specific and verifiable?
2.  **Do NOT add more test cases.** Focus on improving the existing ones.
3.  **Refine and enhance the test cases.** Improve titles, add more specific details to steps and expected results, and correct any mistakes.
4.  **Maintain the original output format ({output_format}).** The final output must be a single, valid {output_format} text, just like the input. Do not add any extra commentary or explanation outside of the test case structure.

Now, provide the improved version of the test cases.
"""


async def _critic_pass(original_text: str, generated_cases: str, output_format: str) -> str:
    """
    Performs the critic pass to refine generated test cases.
    """
    if len(generated_cases) > 10000:  # Safety limit for input to critic
        logging.warning("Generated cases are too long for critic pass, returning initial version.")
        return generated_cases

    prompt = get_critic_prompt(original_text, generated_cases, output_format)

    logging.info(f"Performing critic pass for test cases in '{output_format}' format.")

    try:
        response = await client.aio.models.generate_content(
            model=MODEL_NAME, contents=prompt, config=GENERATION_CONFIG
        )
        # Clean up the response text from potential markdown code blocks
        refined_text = response.text
        if output_format == 'json' and refined_text.startswith("```json"):
            refined_text = refined_text.strip("```json").strip("```")
        if output_format == 'markdown' and refined_text.startswith("```markdown"):
            refined_text = refined_text.strip("```markdown").strip("```")
        if output_format == 'csv' and refined_text.startswith("```csv"):
            refined_text = refined_text.strip("```csv").strip("```")

        return refined_text.strip()
    except Exception as e:
        logging.error(f"Error during critic pass with Gemini: {e}")
        # Fallback to the original generated cases if critic fails
        return generated_cases


async def _initial_generation_pass(raw_text: str, output_format: str, template_type: str, history: list = None) -> str:
    """
    Generates test cases from raw text using the Gemini API. (First pass)
    """
    if len(raw_text) > 4000:  # Safety limit
        raw_text = raw_text[:4000]

    prompt = get_base_prompt(output_format, template_type, history) + raw_text

    logging.info(f"Generating test cases with format '{output_format}' and template '{template_type}'.")

    try:
        response = await client.aio.models.generate_content(
            model=MODEL_NAME, contents=prompt, config=GENERATION_CONFIG
        )
        # Clean up the response text from potential markdown code blocks
        generated_text = response.text
        if output_format == 'json' and generated_text.startswith("```json"):
            generated_text = generated_text.strip("```json").strip("```")
        if output_format == 'markdown' and generated_text.startswith("```markdown"):
            generated_text = generated_text.strip("```markdown").strip("```")
        if output_format == 'csv' and generated_text.startswith("```csv"):
            generated_text = generated_text.strip("```csv").strip("```")

        return generated_text.strip()
    except Exception as e:
        logging.error(f"Error generating content with Gemini: {e}")
        return "Sorry, there was an error generating the test cases. Please try again later."


async def generate_test_cases(raw_text: str, output_format: str, template_type: str, history: list = None) -> str:
    """
    Generates and refines test cases using a two-pass approach (generation + critic).
    """
    # Pass 1: Initial Generation
    initial_test_cases = await _initial_generation_pass(raw_text, output_format, template_type, history)

    # Check if the initial generation failed
    if "Sorry, there was an error" in initial_test_cases:
        return initial_test_cases

    # Pass 2: Critic
    refined_test_cases = await _critic_pass(raw_text, initial_test_cases, output_format)

    return refined_test_cases


def get_endpoint_prompt(output_format: str, method: str, endpoint: str, body: dict = None) -> str:
    """Constructs a prompt for generating test cases for a specific endpoint."""

    body_prompt = f"and the following JSON body:\n```json\n{body}\n```" if body else ""

    prompt = f"""
You are an expert QA automation engineer. Your task is to generate a comprehensive set of test cases for a given API endpoint.

**Output Format:**
Respond in {output_format}. Ensure the response is a single, valid {output_format} text.

**API Endpoint:**
`{method} {endpoint}`
{body_prompt}

**Generation Guidelines:**
- Generate a variety of test cases, including:
  - **Positive tests:** Valid requests, expected status codes (200, 201, 204).
  - **Negative tests:** Invalid input, missing fields, incorrect data types.
  - **Security tests:** Check for authentication (401/403), authorization, and common vulnerabilities like injection.
  - **Performance/Edge cases:** Boundary values, large payloads, concurrency issues.
- For each test case, provide a clear title, steps to reproduce, and expected results (including status code and body assertions).
- Pay close attention to the structure of the provided JSON body to generate relevant tests for its fields.

Now, generate the test cases.
"""
    return prompt


def get_endpoint_critic_prompt(method: str, endpoint: str, body: dict, generated_cases: str, output_format: str) -> str:
    """Constructs the prompt for the endpoint critic pass."""
    body_prompt = f"with the following JSON body:\n```json\n{body}\n```" if body else ""
    return f"""
You are a world-class QA automation engineer acting as a critic.
Your task is to review a set of auto-generated API test cases and improve them.

**Original API Endpoint:**
`{method} {endpoint}`
{body_prompt}

**Generated Test Cases ({output_format}):**
---
{generated_cases}
---

**Your Task:**
1.  **Review the generated test cases for quality.** Look for weak assertions, incorrect status codes, or missed security vulnerabilities (e.g., authentication, authorization). Are there enough negative cases for field validation?
2.  **Do NOT add more test cases.** Focus on improving the existing ones.
3.  **Refine and enhance the test cases.** Make assertions more specific (e.g., "response body contains a 'token' field with a JWT format" instead of just "body is valid"). Improve clarity of steps.
4.  **Maintain the original output format ({output_format}).** The final output must be a single, valid {output_format} text. Do not add any extra commentary.

Now, provide the improved version of the API test cases.
"""


async def _endpoint_critic_pass(
    method: str, endpoint: str, body: dict, generated_cases: str, output_format: str
) -> str:
    """
    Performs the critic pass to refine generated endpoint test cases.
    """
    if len(generated_cases) > 10000:  # Safety limit for input to critic
        logging.warning("Generated endpoint cases are too long for critic pass, returning initial version.")
        return generated_cases

    prompt = get_endpoint_critic_prompt(method, endpoint, body, generated_cases, output_format)

    logging.info(f"Performing critic pass for endpoint '{method} {endpoint}'.")

    try:
        response = await client.aio.models.generate_content(
            model=MODEL_NAME, contents=prompt, config=GENERATION_CONFIG
        )
        # Clean up the response text
        refined_text = response.text.strip()
        if refined_text.startswith(f"```{output_format}"):
            refined_text = refined_text[len(output_format) + 4:-3].strip()

        return refined_text
    except Exception as e:
        logging.error(f"Error during endpoint critic pass with Gemini: {e}")
        # Fallback to the original generated cases if critic fails
        return generated_cases


async def _initial_endpoint_generation_pass(
    output_format: str, method: str, endpoint: str, body: dict = None
) -> str:
    """
    Generates test cases for a specific endpoint using the Gemini API. (First pass)
    """
    prompt = get_endpoint_prompt(output_format, method, endpoint, body)

    logging.info(f"Generating test cases for endpoint '{method} {endpoint}'.")

    try:
        response = await client.aio.models.generate_content(
            model=MODEL_NAME, contents=prompt, config=GENERATION_CONFIG
        )
        # Clean up the response text
        generated_text = response.text.strip()
        if generated_text.startswith(f"```{output_format}"):
            generated_text = generated_text[len(output_format) + 4:-3].strip()

        return generated_text
    except Exception as e:
        logging.error(f"Error generating endpoint test cases with Gemini: {e}")
        return "Sorry, there was an error generating the test cases for the endpoint."


async def generate_endpoint_test_cases(
    output_format: str, method: str, endpoint: str, body: dict = None, history: list = None
) -> str:
    """
    Generates and refines endpoint test cases using a two-pass approach.
    """
    initial_cases = await _initial_endpoint_generation_pass(output_format, method, endpoint, body)

    if "Sorry, there was an error" in initial_cases:
        return initial_cases

    refined_cases = await _endpoint_critic_pass(method, endpoint, body, initial_cases, output_format)
    return refined_cases
