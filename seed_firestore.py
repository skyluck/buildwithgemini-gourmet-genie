"""Seed Firestore with recipe catalog items for GourmetGenie."""
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-c1a943031ac1"

SAMPLE_RECIPES = [
    {
        "id": "mediterranean-quinoa-bowl",
        "title": "Mediterranean Quinoa Power Bowl",
        "cuisine": "Mediterranean",
        "difficulty": "Easy",
        "prep_time_minutes": 20,
        "calories_per_serving": 420,
        "dietary_tags": ["Vegetarian", "Gluten-Free", "High-Protein"],
        "ingredients": [
            "1 cup cooked quinoa",
            "1/2 cup diced cucumbers",
            "1/2 cup cherry tomatoes",
            "1/4 cup kalamata olives",
            "1/4 cup crumbled feta cheese",
            "2 tbsp extra virgin olive oil",
            "1 tbsp fresh lemon juice",
            "1 tbsp chopped fresh mint"
        ],
        "instructions": [
            "Fluff cooked quinoa and add to a wide serving bowl.",
            "Toss cucumbers, cherry tomatoes, and kalamata olives with olive oil and lemon juice.",
            "Top quinoa with vegetable mixture and crumbled feta.",
            "Garnish with chopped mint and a crack of black pepper."
        ]
    },
    {
        "id": "lemon-herb-grilled-salmon",
        "title": "Lemon Herb Grilled Salmon with Asparagus",
        "cuisine": "American / Healthy",
        "difficulty": "Medium",
        "prep_time_minutes": 25,
        "calories_per_serving": 480,
        "dietary_tags": ["Keto", "High-Protein", "Gluten-Free", "Pescatarian"],
        "ingredients": [
            "2 salmon fillets (6 oz each)",
            "1 bunch fresh asparagus, trimmed",
            "2 tbsp olive oil",
            "2 cloves garlic, minced",
            "1 tbsp chopped fresh dill",
            "1 lemon, sliced into rounds",
            "Sea salt and black pepper to taste"
        ],
        "instructions": [
            "Preheat grill or skillet to medium-high heat.",
            "Toss asparagus with 1 tbsp olive oil, salt, and pepper.",
            "Brush salmon with remaining olive oil, minced garlic, dill, salt, and pepper.",
            "Grill salmon for 4-5 minutes per side until flaky, grilling lemon slices and asparagus alongside."
        ]
    },
    {
        "id": "thai-coconut-tofu-curry",
        "title": "Creamy Thai Coconut Tofu Curry",
        "cuisine": "Thai",
        "difficulty": "Medium",
        "prep_time_minutes": 30,
        "calories_per_serving": 510,
        "dietary_tags": ["Vegan", "Dairy-Free", "Gluten-Free"],
        "ingredients": [
            "1 block extra firm tofu, pressed and cubed",
            "1 can (13.5 oz) full-fat coconut milk",
            "2 tbsp red curry paste",
            "1 red bell pepper, sliced",
            "1 cup sugar snap peas",
            "1 tbsp soy sauce or tamari",
            "1 tbsp coconut oil",
            "Fresh cilantro and lime wedges"
        ],
        "instructions": [
            "Heat coconut oil in a pan over medium heat and sear tofu cubes until golden on all sides.",
            "Add red curry paste and sauté for 1 minute until fragrant.",
            "Pour in coconut milk and tamari, bringing to a simmer.",
            "Stir in bell pepper and snap peas; simmer for 5 minutes until tender-crisp.",
            "Serve hot topped with fresh cilantro and a squeeze of lime juice."
        ]
    },
    {
        "id": "tuscan-white-bean-soup",
        "title": "Rustic Tuscan White Bean & Kale Soup",
        "cuisine": "Italian",
        "difficulty": "Easy",
        "prep_time_minutes": 25,
        "calories_per_serving": 340,
        "dietary_tags": ["Vegan", "High-Fiber", "Low-Fat"],
        "ingredients": [
            "2 cans (15 oz) cannellini beans, drained and rinsed",
            "4 cups vegetable broth",
            "2 cups chopped Tuscan kale leaves",
            "1 medium carrot, diced",
            "1 celery stalk, diced",
            "1/2 yellow onion, diced",
            "2 cloves garlic, minced",
            "1 tsp dried rosemary"
        ],
        "instructions": [
            "Sauté onion, carrot, celery, and garlic in a soup pot with olive oil until softened.",
            "Add cannellini beans, dried rosemary, and vegetable broth. Bring to a gentle boil.",
            "Partially mash 1/3 of the beans with a fork to thicken the broth naturally.",
            "Stir in chopped kale and simmer for 5-8 minutes until tender. Season with salt and pepper."
        ]
    }
]

def seed():
    db = firestore.Client(project=PROJECT_ID)
    recipes_ref = db.collection("recipes")
    print(f"Seeding recipes into Firestore project: {PROJECT_ID}...")
    for recipe in SAMPLE_RECIPES:
        doc_id = recipe["id"]
        recipes_ref.document(doc_id).set(recipe)
        print(f"  ✓ Added recipe: {recipe['title']} (id: {doc_id})")
    print("Seeding complete!")

if __name__ == "__main__":
    seed()
