# GourmetGenie — AI Personal Chef & Meal Planner

GourmetGenie is an intelligent conversational culinary assistant built with Google Agent Development Kit (ADK) and deployed on Google Cloud Agent Platform (Vertex AI Agent Engine). It helps home cooks discover curated recipes, personalize meals based on cross-session dietary restrictions, generate smart grocery lists, locate local specialty markets, calculate nutritional metrics in a secure code sandbox, and visualize plated dishes.

---

## What the Agent Does

GourmetGenie is equipped with the following production-wired capabilities:

- **Cross-Session Memory & Allergy Safety (Vertex AI Memory Bank)**:
  - Uses `PreloadMemoryTool` and an automated `after_agent_callback` (`add_session_to_memory`) wired to Vertex AI Memory Bank.
  - Automatically captures, remembers, and recalls user allergies, dietary restrictions, family sizes, and flavor preferences across distinct sessions and conversations.
- **Recipe Management & Catalog (Cloud Firestore)**:
  - `list_recipes`: Queries Firestore (`recipes` collection) filtering by cuisine, dietary tags (e.g. Vegetarian, Gluten-Free, Keto), and max calories.
  - `get_recipe_details`: Retrieves full ingredient measurements, instructions, and metadata.
  - `save_recipe`: Persists newly generated or customized recipes into Firestore.
- **Smart Grocery List Generation**:
  - `generate_grocery_list`: Compiles an aggregated shopping list across multiple selected recipes, automatically cross-referencing and subtracting items already on hand in the user's pantry.
- **Global Culinary Search**:
  - `search_global_recipes`: Integrates with TheMealDB API to fetch international recipe ideas and culinary inspirations.
- **Local Store & Market Locator (Google Maps Platform)**:
  - `geocode_address`: Resolves user addresses or city locations to geographical coordinates via Google Maps Geocoding API.
  - `find_nearby_places`: Searches for nearby supermarkets, grocery stores, bakeries, or specialty grocers using Google Places API (New).
- **Dish Visualization (Gemini Image Generation & Cloud Storage)**:
  - `generate_dish_image`: Generates photorealistic culinary plating visuals using `gemini-3.1-flash-lite-image` via the Google GenAI SDK.
  - Saves the image as an ADK session artifact and uploads it directly to Google Cloud Storage (`gs://<bucket>/dishes/...`), returning a public HTTPS URL.
- **Nutritional & Macro Math (Agent Engine Code Sandbox)**:
  - Leverages `AgentEngineSandboxCodeExecutor` (`google.adk.code_executors`) to safely run isolated Python code in Google Cloud's sandbox environment for calculating exact calorie distributions, macro ratios, and ingredient scaling.
- **Rich Display UI (A2UI v0.8)**:
  - Generates structured A2UI declarative surfaces (`Card`, `Column`, `Row`, `Text`, `Image`) via `A2uiSchemaManager` and an `after_model_callback` (`a2ui_callback`), rendered directly in both ADK Web and the custom frontend.

*(Note: Live grocery store pricing feeds mentioned in early concept planning are planned, not yet implemented.)*

---

## Google Cloud Services Wired

| Cloud Service | Purpose in GourmetGenie |
| :--- | :--- |
| **Vertex AI Agent Engine (Reasoning Engine)** | Hosts the autonomous agent runtime over the A2A protocol. |
| **Vertex AI Memory Bank** | Manages persistent user profile memories, allergies, and conversation facts. |
| **Agent Engine Code Sandbox** | Runs untrusted Python code in an isolated VM for macro & scaling computations. |
| **Cloud Firestore** | Stores curated recipes and user-created dishes. |
| **Cloud Storage** | Stores generated dish plating images served publicly via HTTPS. |
| **Gemini 2.5 Flash & Flash Lite Image** | Core reasoning LLM and multimodal image generation model. |
| **Cloud Run** | Hosts the lightweight FastAPI proxy and chat interface container. |

---

## Project Structure

```
gourmet-genie/
├── app/
│   ├── agent.py               # Core agent definition, tools, and callbacks
│   ├── a2ui_schema_adapter.py # A2UI v0.8 schema prompt adapter
│   ├── a2ui_utils.py          # A2UI after-model callback renderer
│   ├── fast_api_app.py        # Local FastAPI ADK app entrypoint
│   └── app_utils/             # A2A protocol & reasoning engine adapters
├── frontend/
│   ├── main.py                # FastAPI A2A proxy server
│   ├── requirements.txt       # Frontend proxy dependencies
│   ├── Dockerfile             # Container configuration for Cloud Run
│   └── static/
│       └── index.html         # Dialogue chat UI with A2UI renderer & prompt chips
├── seed_firestore.py          # Script to populate sample recipes in Firestore
├── agents-cli-manifest.yaml   # Agent Engine deployment manifest
├── deployment_metadata.json   # Remote Agent Engine resource metadata
├── pyproject.toml             # Agent Python package & dependencies
└── README.md
```

---

## Local Setup & Run Instructions

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Google Cloud CLI (`gcloud`)](https://cloud.google.com/sdk/docs/install) authenticated with Application Default Credentials (`gcloud auth application-default login`)

### 1. Agent Development & Playground

1. Clone or navigate to the repository:
   ```bash
   cd gourmet-genie
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. (Optional) Seed the Firestore database with sample recipes:
   ```bash
   uv run python seed_firestore.py
   ```

4. Launch the ADK development playground:
   ```bash
   uv run adk web . --port 8080 --reload_agents
   ```

---

### 2. Running the Frontend Proxy Locally

The frontend connects to the deployed Agent Runtime via the A2A (Agent-to-Agent) protocol.

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   uv venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Set your environment variables:
   ```bash
   export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/<REGION>/reasoningEngines/<ENGINE_ID>"
   export AGENT_DIRECTORY="app"
   ```

4. Start the frontend proxy server:
   ```bash
   python main.py
   ```

---

## Deployment Instructions

### Deploy Agent to Vertex AI Agent Engine

Deploy the agent logic to Google Cloud Agent Platform using `agents-cli`:
```bash
agents-cli deploy --project <PROJECT_ID> --update-env-vars GOOGLE_MAPS_API_KEY=<YOUR_KEY>
```

### Deploy Frontend to Cloud Run

From the `frontend/` directory:
```bash
gcloud run deploy gourmet-genie-frontend \
  --source . \
  --region us-east1 \
  --project <PROJECT_ID> \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="<RESOURCE_NAME>",AGENT_DIRECTORY="app" \
  --allow-unauthenticated
```
Ensure the Cloud Run service account has `roles/aiplatform.user` granted to communicate with the Agent Engine.
