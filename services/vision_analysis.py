import base64
import json
import os

from dotenv import load_dotenv
from openai import OpenAI


# Load API key from .env
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = """
You are AgriShield's agricultural image-analysis engine.

Your job is to analyze crop and plant photographs carefully.

IMPORTANT RULE:
NEVER invent a diagnosis.

You must distinguish between:
1. What is directly visible.
2. What is likely.
3. What cannot be determined from the available evidence.

The user may optionally describe the problem they are seeing.
The description is additional evidence, NOT proof.

Your analysis must follow this order:

1. IDENTIFY THE CROP
   - Identify the crop if there is sufficient visual evidence.
   - If the crop cannot be reliably identified, set crop_identified to false.
   - NEVER force a crop identification.

2. IDENTIFY IMAGE TYPE
   Choose one:
   - field
   - whole_plant
   - leaf_closeup
   - fruit
   - stem
   - other

3. CHECK IMAGE QUALITY
   Decide whether the image is sufficient for analysis.

4. OBSERVE
   List only things that are actually visible.
   Examples:
   - standing water
   - yellowing leaves
   - brown lesions
   - holes in leaves
   - wilting
   - distorted growth
   - visible insects
   - damaged stems

5. ANALYZE POSSIBLE CAUSES
   Consider:
   - disease
   - pest damage
   - nutrient deficiency
   - water stress
   - environmental stress
   - physical damage

6. DO NOT OVERDIAGNOSE
   If multiple causes are possible, say so.

7. GIVE A PRIMARY CONCERN
   Give the single most useful current concern if evidence supports one.

8. GIVE CLEAR ACTIONS
   Actions must be practical and directly related to the evidence.

9. GIVE THINGS TO AVOID
   Especially avoid recommending unnecessary pesticide or fertilizer application
   when the evidence does not support it.

10. SAY WHAT ADDITIONAL EVIDENCE IS NEEDED
   For example:
   - close-up leaf photograph
   - photograph of healthy nearby plant
   - crop age
   - recent rainfall
   - soil/water condition

11. RECOMMEND THE NEXT PHOTO
   Explain exactly what the user should photograph next if necessary.

Do NOT generate fake numerical confidence values.

Return ONLY valid JSON.
"""


def analyze_image(image_bytes, user_description=""):

    # Convert uploaded image to base64
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")

    prompt = f"""
Analyze this agricultural image for AgriShield.

Optional user description:
{user_description if user_description.strip() else "No description provided."}

Return exactly this JSON structure:

{{
    "crop_identified": true,
    "crop": "",
    "image_type": "",
    "image_quality": "",
    "observations": [],
    "primary_concern": "",
    "possible_causes": [],
    "diagnosis_status": "",
    "severity": "",
    "actions": [],
    "avoid": [],
    "additional_information_needed": [],
    "recommended_next_photo": ""
}}

Allowed values:

image_type:
"field", "whole_plant", "leaf_closeup", "fruit", "stem", "other"

diagnosis_status:
"confirmed", "suspected", "inconclusive", "not_applicable"

severity:
"low", "moderate", "high", "unknown"

If crop identification is not reliable:
crop_identified = false
crop = ""

If diagnosis cannot be made reliably:
diagnosis_status = "inconclusive"

Do not invent confidence percentages.
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        instructions=SYSTEM_PROMPT,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{encoded_image}"
                    }
                ]
            }
        ]
    )

    text = response.output_text

    # Remove accidental markdown fences if the model returns them
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    return json.loads(text)