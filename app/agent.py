# ruff: noqa
import datetime
from zoneinfo import ZoneInfo
from typing import List, Optional, Dict, Any

import os
import requests
import dotenv
dotenv.load_dotenv()

from app.a2ui_schema_adapter import A2uiSchemaManager, BasicCatalog
from app.a2ui_utils import a2ui_callback
from google.cloud import firestore, storage
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import (
    AgentEngineSandboxCodeExecutor,
)
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

MODEL = "gemini-3.8-flash"
PROJECT_ID = "qwiklabs-gcp-04-c1a943031ac1"
LOCATION = "us-east1"
MEMORY_BANK_ID = "2257067573893922816"
BUCKET_NAME = "gourmet-genie-dishes-qwiklabs-gcp-04-c1a943031ac1"
SANDBOX_RESOURCE_NAME = (
    "projects/845922113024/locations/us-east1/reasoningEngines/2257067573893922816"
    "/sandboxEnvironments/2800537479805927424"
)


def get_firestore_client() -> firestore.Client:
    """Returns a Firestore client initialized with hardcoded project ID."""
    return firestore.Client(project=PROJECT_ID)


def list_recipes(
    cuisine: Optional[str] = None,
    dietary_tag: Optional[str] = None,
    max_calories: Optional[int] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Search and list curated recipes from the Firestore database.

    Args:
        cuisine: Optional cuisine filter (e.g., 'Mediterranean', 'Thai', 'Italian').
        dietary_tag: Optional dietary tag filter (e.g., 'Vegetarian', 'Vegan', 'Keto', 'Gluten-Free').
        max_calories: Optional maximum calories per serving.
        limit: Maximum number of recipes to return (default: 5).

    Returns:
        A list of matching recipe dictionaries.
    """
    db = get_firestore_client()
    recipes_ref = db.collection("recipes")
    docs = recipes_ref.stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id

        if cuisine and cuisine.lower() not in data.get("cuisine", "").lower():
            continue

        if dietary_tag:
            tags = [t.lower() for t in data.get("dietary_tags", [])]
            if dietary_tag.lower() not in tags:
                continue

        if max_calories and data.get("calories_per_serving", 0) > max_calories:
            continue

        results.append(data)
        if len(results) >= limit:
            break

    return results


def get_recipe_details(recipe_id: str) -> Dict[str, Any]:
    """Retrieve full details, ingredients, and instructions for a specific recipe.

    Args:
        recipe_id: The document ID of the recipe (e.g., 'mediterranean-quinoa-bowl').

    Returns:
        The recipe dictionary if found, or an error dictionary.
    """
    db = get_firestore_client()
    doc = db.collection("recipes").document(recipe_id).get()
    if not doc.exists:
        return {"error": f"Recipe with ID '{recipe_id}' not found."}
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def save_recipe(
    title: str,
    cuisine: str,
    difficulty: str,
    prep_time_minutes: int,
    calories_per_serving: int,
    ingredients: List[str],
    instructions: List[str],
    dietary_tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Save a newly created or customized recipe to the Firestore database.

    Args:
        title: The name of the recipe.
        cuisine: Type of cuisine (e.g. 'French', 'Mexican', 'Asian').
        difficulty: 'Easy', 'Medium', or 'Hard'.
        prep_time_minutes: Preparation time in minutes.
        calories_per_serving: Estimated calories per serving.
        ingredients: List of ingredient strings with quantities.
        instructions: Step-by-step cooking instructions.
        dietary_tags: Optional dietary tags like 'Vegan', 'Keto', 'High-Protein'.

    Returns:
        Confirmation dictionary with the created recipe ID.
    """
    db = get_firestore_client()
    slug = title.lower().strip().replace(" ", "-").replace("/", "-")
    doc_id = "".join(c for c in slug if c.isalnum() or c == "-")[:40]

    recipe_data = {
        "id": doc_id,
        "title": title,
        "cuisine": cuisine,
        "difficulty": difficulty,
        "prep_time_minutes": prep_time_minutes,
        "calories_per_serving": calories_per_serving,
        "ingredients": ingredients,
        "instructions": instructions,
        "dietary_tags": dietary_tags or [],
    }

    db.collection("recipes").document(doc_id).set(recipe_data)
    return {"status": "success", "message": f"Recipe '{title}' saved successfully.", "recipe_id": doc_id}


def generate_grocery_list(
    recipe_ids: List[str],
    on_hand_ingredients: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generates a shopping grocery list for one or more recipes, subtracting items already on hand.

    Args:
        recipe_ids: List of recipe document IDs to cook (e.g. ['mediterranean-quinoa-bowl']).
        on_hand_ingredients: Optional list of ingredient names the user already has in their pantry (e.g. ['salt', 'olive oil']).

    Returns:
        A dictionary containing the recipe titles, items on hand, and needed grocery items.
    """
    db = get_firestore_client()
    needed_items = []
    recipes_included = []
    pantry_set = {item.strip().lower() for item in (on_hand_ingredients or [])}

    for rid in recipe_ids:
        doc = db.collection("recipes").document(rid).get()
        if not doc.exists:
            continue
        data = doc.to_dict()
        recipes_included.append(data.get("title", rid))
        for ing in data.get("ingredients", []):
            ing_lower = ing.lower()
            # If the ingredient is not covered by any on-hand pantry item
            if not any(pantry_item in ing_lower for pantry_item in pantry_set if pantry_item):
                needed_items.append(ing)

    return {
        "recipes": recipes_included,
        "on_hand_excluded": list(pantry_set),
        "grocery_list": needed_items,
        "total_items_to_buy": len(needed_items),
    }


def search_global_recipes(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Search for real-world global recipes and culinary ideas via TheMealDB public API.

    Args:
        query: Ingredient or dish name to search for (e.g. 'salmon', 'pasta', 'curry', 'tofu').
        limit: Maximum number of recipe ideas to return (default: 3).

    Returns:
        A list of simplified recipe summaries from TheMealDB.
    """
    api_key = os.environ.get("MEALDB_API_KEY", "1")
    url = f"https://www.themealdb.com/api/json/v1/{api_key}/search.php"
    try:
        resp = requests.get(url, params={"s": query}, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        meals = data.get("meals") or []
    except Exception as e:
        return [{"error": f"Failed to fetch global recipes: {str(e)}"}]

    results = []
    for meal in meals[:limit]:
        # Extract non-empty ingredients
        ingredients = []
        for i in range(1, 21):
            ing = meal.get(f"strIngredient{i}")
            measure = meal.get(f"strMeasure{i}")
            if ing and ing.strip():
                measure_str = f" ({measure.strip()})" if measure and measure.strip() else ""
                ingredients.append(f"{ing.strip()}{measure_str}")

        results.append({
            "title": meal.get("strMeal"),
            "category": meal.get("strCategory"),
            "cuisine": meal.get("strArea"),
            "thumbnail_url": meal.get("strMealThumb"),
            "ingredients": ingredients,
            "instructions_preview": (meal.get("strInstructions") or "")[:250] + "...",
        })

    return results


def geocode_address(address: str) -> Dict[str, Any]:
    """Uses Google Maps Geocoding API to turn an address or place into coordinates.

    Args:
        address: Street address, city, or landmark (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A dictionary with formatted address, latitude, and longitude.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return {"error": "GOOGLE_MAPS_API_KEY is not configured in environment."}

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    try:
        resp = requests.get(url, params={"address": address, "key": api_key}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK" or not data.get("results"):
            return {"error": f"Geocoding failed: {data.get('status')}", "error_message": data.get("error_message")}

        top_result = data["results"][0]
        location = top_result["geometry"]["location"]
        return {
            "formatted_address": top_result.get("formatted_address"),
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "place_id": top_result.get("place_id"),
        }
    except Exception as e:
        return {"error": f"Geocoding request failed: {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "grocery_store",
    radius_meters: float = 2000.0,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """Uses Google Maps Places API (New) to search for nearby places around coordinates.

    Args:
        latitude: Latitude coordinate.
        longitude: Longitude coordinate.
        place_type: Type of place to search for (e.g. 'supermarket', 'grocery_store', 'bakery', 'restaurant').
        radius_meters: Search radius in meters (default 2000.0, max 50000.0).
        max_results: Maximum results to return (between 1 and 20).

    Returns:
        A list of nearby places with name, address, and location coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return [{"error": "GOOGLE_MAPS_API_KEY is not configured in environment."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types",
    }
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": min(max(max_results, 1), 20),
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": float(radius_meters),
            }
        },
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        places = data.get("places") or []
        results = []
        for p in places:
            display_name = p.get("displayName", {}).get("text")
            address = p.get("formattedAddress")
            loc = p.get("location", {})
            results.append({
                "name": display_name,
                "address": address,
                "location": {
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                },
                "types": p.get("types", []),
            })
        return results
    except Exception as e:
        return [{"error": f"Places API search failed: {str(e)}"}]


async def generate_dish_image(
    dish_name: str,
    styling_description: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generates a high-quality culinary visual for a dish using gemini-3.1-flash-lite-image in the global region.
    Saves the image as a local artifact for the Playground and uploads it to public Cloud Storage.

    Args:
        dish_name: The name of the dish (e.g. 'Mediterranean Quinoa Power Bowl').
        styling_description: Visual styling instructions (e.g. 'Served in a ceramic bowl on a rustic wooden table with fresh herbs, soft natural lighting').

    Returns:
        A dictionary with the public HTTPS URL, artifact filename, and status.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    prompt = (
        f"Professional culinary photography of {dish_name}. "
        f"{styling_description}. High resolution, appetizing presentation, beautifully plated."
    )

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )
    except Exception as e:
        return {"error": f"Image generation failed: {str(e)}"}

    image_bytes = None
    mime_type = "image/jpeg"
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            image_bytes = part.inline_data.data
            mime_type = part.inline_data.mime_type or "image/jpeg"
            break

    if not image_bytes:
        return {"error": "Model did not return image data."}

    ext = "png" if "png" in mime_type else "jpg"
    clean_name = "".join(c if c.isalnum() else "_" for c in dish_name.lower().strip())[:30]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{clean_name}_{timestamp}.{ext}"

    # 1. Save with tool_context.save_artifact so it appears in Playground's Artifacts panel
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    await tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload same bytes directly to Cloud Storage (no local file path) and return public HTTPS URL
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"dishes/{filename}")
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/dishes/{filename}"

    return {
        "status": "success",
        "dish_name": dish_name,
        "artifact_filename": filename,
        "public_url": public_url,
    }


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: after each turn, send the session to Memory Bank for extraction."""
    await callback_context.add_session_to_memory()
    return None


def memory_bank_service_builder():
    """Builds VertexAiMemoryBankService pointed at the deployed Agent Engine."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    )


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are GourmetGenie, an expert Personal Chef and Meal Planner assistant.\n"
        "CRITICAL MEMORY & ALLERGY RULE: You must remember all user allergies, dietary restrictions, and food intolerances "
        "stated across conversations without exception. Whenever a user mentions any allergy (e.g., peanuts, shellfish, gluten, dairy, "
        "soy, eggs, tree nuts, etc.), explicitly acknowledge and confirm it so it is permanently captured in memory. "
        "Always cross-reference preloaded memories and never suggest, generate, or include ingredients that conflict with remembered allergies.\n"
        "You also remember the user's stated dietary goals, pantry items, and flavor preferences from previous conversations "
        "and personalize your recommendations accordingly.\n"
        "You help users discover recipes, customize dishes according to dietary goals or restrictions, "
        "and manage their meal plans and grocery shopping.\n"
        "You have direct access to tools: list_recipes, get_recipe_details, save_recipe, generate_grocery_list, "
        "search_global_recipes, geocode_address, find_nearby_places, and generate_dish_image.\n"
        "When a user asks for recipes, search the curated Firestore database first with list_recipes. If they want broader or global ideas "
        "or if Firestore doesn't have matches, use search_global_recipes to find real-world dishes via TheMealDB API.\n"
        "When a user needs to find local grocery stores, markets, or specialty food suppliers, use geocode_address to get coordinates "
        "and find_nearby_places to find convenient locations.\n"
        "When a user asks to visualize or see a dish, plating, or meal idea, call generate_dish_image to create a gorgeous photo, "
        "which saves it to artifacts and gives you a public Cloud Storage image URL to display.\n"
        "You also have a secure Agent Engine Python sandbox code executor. Use Python code execution to calculate nutritional totals, "
        "scale ingredient measurements, compute macros, or analyze caloric distributions."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        list_recipes,
        get_recipe_details,
        save_recipe,
        generate_grocery_list,
        search_global_recipes,
        geocode_address,
        find_nearby_places,
        generate_dish_image,
    ],
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=SANDBOX_RESOURCE_NAME,
    ),
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
