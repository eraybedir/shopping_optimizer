import pandas as pd
from pulp import LpProblem, LpVariable, lpSum, LpMinimize, LpStatus, value, PULP_CBC_CMD
import re
import os

# --- Category Mapping using C column (item_category) ---
def map_main_group(row):
    item_category = str(row['item_category']).lower()
    name = str(row['name']).lower()
    
    # Exclude granola items
    if 'granola' in item_category or 'granola' in name:
        return 'exclude'
    
    # Vegetables
    if any(keyword in item_category for keyword in ['sebze', 'domates', 'biber', 'salatalık', 'patates', 'soğan', 'havuç']):
        return 'vegetables'
    if any(keyword in name for keyword in ['domates', 'biber', 'salatalık', 'patates', 'soğan', 'havuç', 'kabak']):
        return 'vegetables'
    
    # Fruits
    if any(keyword in item_category for keyword in ['meyve', 'elma', 'muz', 'portakal', 'armut', 'çilek']):
        return 'fruits'
    if any(keyword in name for keyword in ['elma', 'muz', 'portakal', 'armut', 'çilek', 'kayısı', 'şeftali']):
        return 'fruits'
    
    # Dairy
    if any(keyword in item_category for keyword in ['süt', 'kahvalt', 'peynir', 'yoğurt', 'süt ürünleri']):
        return 'dairy'
    if any(keyword in name for keyword in ['peynir', 'yoğurt', 'süt', 'kaymak', 'krema']):
        return 'dairy'
    
    # Legumes
    if any(keyword in item_category for keyword in ['bakliyat', 'fasulye', 'mercimek', 'nohut', 'bezelye']):
        return 'legumes'
    if any(keyword in name for keyword in ['fasulye', 'mercimek', 'nohut', 'bezelye', 'barbunya']):
        return 'legumes'
    
    # Meat/Fish
    if any(keyword in item_category for keyword in ['et', 'balık', 'tavuk', 'kıyma', 'sucuk']):
        return 'meat_fish'
    if any(keyword in name for keyword in ['tavuk', 'balık', 'kıyma', 'sucuk', 'salam', 'pastırma']):
        return 'meat_fish'
    
    # Grains
    if any(keyword in item_category for keyword in ['temel gıda', 'ekmek', 'bulgur', 'pirinç', 'makarna', 'un']):
        return 'grains'
    if any(keyword in name for keyword in ['ekmek', 'bulgur', 'pirinç', 'makarna', 'un', 'börek']):
        return 'grains'
    
    return 'other'

def get_user_input():
    print("\n=== SHOPPING OPTIMIZER v2.0 ===")
    print("Please enter your information:")
    
    # Age validation
    while True:
        try:
            age = int(input("Age: "))
            if 0 < age < 120:
                break
            print("Please enter a valid age between 1 and 120.")
        except ValueError:
            print("Please enter a valid number for age.")

    # Gender validation
    while True:
        gender = input("Gender (male/female): ").strip().lower()
        if gender in ['male', 'female']:
            break
        print("Please enter either 'male' or 'female'.")

    # Weight validation
    while True:
        try:
            weight = float(input("Weight (kg): "))
            if 20 < weight < 300:
                break
            print("Please enter a valid weight between 20 and 300 kg.")
        except ValueError:
            print("Please enter a valid number for weight.")

    # Height validation
    while True:
        try:
            height = float(input("Height (cm): "))
            if 100 < height < 250:
                break
            print("Please enter a valid height between 100 and 250 cm.")
        except ValueError:
            print("Please enter a valid number for height.")

    # Activity level validation
    while True:
        activity = input("Activity level (sedentary/lightly active/moderately active/very active/extra active): ").strip().lower()
        if activity in ['sedentary', 'lightly active', 'moderately active', 'very active', 'extra active']:
            break
        print("Please enter one of the valid activity levels.")

    # Goal validation
    while True:
        goal = input("Goal (gaining weight/doing sports/losing weight/being healthy): ").strip().lower()
        if goal in ['gaining weight', 'doing sports', 'losing weight', 'being healthy']:
            break
        print("Please enter one of the valid goals.")

    # Budget validation
    while True:
        try:
            budget = float(input("Monthly budget (TL): "))
            if budget > 0:
                break
            print("Please enter a positive number for budget.")
        except ValueError:
            print("Please enter a valid number for budget.")

    return age, gender, weight, height, activity, goal, budget

# --- TDEE Calculation ---
def calculate_tdee(age, gender, weight, height, activity):
    # Basal Metabolic Rate (BMR) calculation
    if gender == "male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    
    # Activity level multipliers
    activity_factors = {
        "sedentary": 1.2,
        "lightly active": 1.375,
        "moderately active": 1.55,
        "very active": 1.725,
        "extra active": 1.9
    }
    
    tdee = bmr * activity_factors.get(activity, 1.2)
    return tdee

# --- Macro Targets ---
def get_macro_targets(tdee, goal):
    # Adjust TDEE based on goal
    if "gain" in goal:
        tdee += 200
    elif "lose" in goal:
        tdee -= 200
    
    # Macro ratios based on goal
    if "sport" in goal:
        protein_ratio = 0.20
        fat_ratio = 0.25
        carb_ratio = 0.55
    else:
        protein_ratio = 0.15
        fat_ratio = 0.25
        carb_ratio = 0.60
    
    # Calculate macro targets in grams
    protein_g = (tdee * protein_ratio) / 4  # 4 calories per gram of protein
    fat_g = (tdee * fat_ratio) / 9          # 9 calories per gram of fat
    carb_g = (tdee * carb_ratio) / 4        # 4 calories per gram of carbs
    
    return tdee, protein_g, fat_g, carb_g

def extract_weight(name):
    """Extract weight from product name"""
    match = re.search(r"(\d+[.,]?\d*)\s*(kg|g|gr)", name.lower())
    if match:
        value = float(match.group(1).replace(",", "."))
        unit = match.group(2)
        if "kg" in unit:
            return int(value * 1000)  # Convert kg to grams
        else:
            return int(value)  # Already in grams
    return 1000  # Default weight in grams

# --- Data Preprocessing ---
def preprocess_data(df):
    print("Preprocessing data...")
    
    # Clean price column
    df["price"] = df["price"].astype(str).str.replace(" TL", "", regex=False)
    df["price"] = df["price"].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    
    # Clean nutrition columns
    for col in ["calories", "protein", "carbs", "fat"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Remove rows with missing or invalid data
    df = df.dropna(subset=["price", "calories", "protein", "carbs", "fat"])
    df = df[(df["price"] > 0) & (df["calories"] >= 0) & (df["protein"] >= 0) & 
            (df["carbs"] >= 0) & (df["fat"] >= 0)]
    
    # Exclude beverages
    df = df[~df["category"].str.lower().str.contains("içecek")]
    
    # Exclude noodles
    df = df[~df["name"].str.lower().str.contains("noodle")]
    df = df[~df["item_category"].str.lower().str.contains("noodle")]
    
    # Exclude liver and heart products
    df = df[~df["name"].str.lower().str.contains("ciğer")]
    df = df[~df["name"].str.lower().str.contains("yürek")]
    df = df[~df["name"].str.lower().str.contains("liver")]
    df = df[~df["name"].str.lower().str.contains("heart")]
    
    # Exclude products containing 'çabuk' or 'bardak' (Turkish only)
    df = df[~df["name"].str.lower().str.contains("çabuk")]
    df = df[~df["name"].str.lower().str.contains("bardak")]
    
    # Exclude Berliner and Kruvasan products
    df = df[~df["name"].str.lower().str.contains("berliner")]
    df = df[~df["name"].str.lower().str.contains("kruvasan")]
    df = df[~df["name"].str.lower().str.contains("croissant")]
    
    # Exclude products containing 'pilavı' and 'çikolata'
    df = df[~df["name"].str.lower().str.contains("pilavı")]
    df = df[~df["name"].str.lower().str.contains("çikolata")]
    
    # Extract weight from product names
    df["weight_g"] = df["name"].apply(extract_weight)
    
    # Apply filters
    df = df[df["weight_g"] <= 5000]  # Max 5kg per item
    df = df[df["price"] <= 1000]     # Max 1000 TL per item
    df = df[df["calories"] > 0]      # Must have calories
    
    # Map categories using C column (item_category)
    df['main_group'] = df.apply(map_main_group, axis=1)
    
    # Exclude granola items
    df = df[df['main_group'] != 'exclude']
    
    print(f"Data preprocessing complete: {len(df)} products available")
    print(f"Price range: {df['price'].min():.2f} - {df['price'].max():.2f} TL")
    print(f"Calories range: {df['calories'].min():.0f} - {df['calories'].max():.0f} kcal")
    print(f"Average price: {df['price'].mean():.2f} TL")
    print(f"Average calories: {df['calories'].mean():.0f} kcal")
    
    return df

# --- Optimization ---
def optimize_shopping(df, tdee, protein_g, fat_g, carb_g, budget, days=30):
    print(f"\n=== OPTIMIZATION PARAMETERS ===")
    print(f"Budget: {budget} TL")
    print(f"Required calories: {tdee * days:.0f} kcal")
    print(f"Required protein: {protein_g * days:.0f} g")
    print(f"Required fat: {fat_g * days:.0f} g")
    print(f"Required carbs: {carb_g * days:.0f} g")
    print(f"Available products: {len(df)}")
    
    # Check if we have enough products in each category
    print(f"\n=== CATEGORY ANALYSIS ===")
    for group in ['vegetables', 'fruits', 'dairy', 'legumes', 'meat_fish', 'grains']:
        group_products = df[df['main_group'] == group]
        print(f"{group}: {len(group_products)} products")
        if len(group_products) == 0:
            print(f"⚠️  WARNING: No products found in {group} category!")
    
    # Check nutrition feasibility
    print(f"\n=== NUTRITION FEASIBILITY CHECK ===")
    total_calories_available = df['calories'].sum() * 5  # Max 5 of each item
    total_protein_available = df['protein'].sum() * 5
    total_fat_available = df['fat'].sum() * 5
    total_carbs_available = df['carbs'].sum() * 5
    
    print(f"Available calories (max): {total_calories_available:.0f} kcal")
    print(f"Required calories: {tdee * days:.0f} kcal")
    print(f"Feasible: {'✅' if total_calories_available >= tdee * days else '❌'}")
    
    print(f"Available protein (max): {total_protein_available:.0f} g")
    print(f"Required protein: {protein_g * days:.0f} g")
    print(f"Feasible: {'✅' if total_protein_available >= protein_g * days else '❌'}")
    
    print(f"Available fat (max): {total_fat_available:.0f} g")
    print(f"Required fat: {fat_g * days:.0f} g")
    print(f"Feasible: {'✅' if total_fat_available >= fat_g * days else '❌'}")
    
    print(f"Available carbs (max): {total_carbs_available:.0f} g")
    print(f"Required carbs: {carb_g * days:.0f} g")
    print(f"Feasible: {'✅' if total_carbs_available >= carb_g * days else '❌'}")
    
    # Check budget feasibility
    print(f"\n=== BUDGET FEASIBILITY CHECK ===")
    min_cost = df['price'].min()
    max_cost = df['price'].max()
    avg_cost = df['price'].mean()
    print(f"Product price range: {min_cost:.2f} - {max_cost:.2f} TL")
    print(f"Average product price: {avg_cost:.2f} TL")
    print(f"Budget: {budget:.2f} TL")
    print(f"Minimum budget needed (70%): {budget * 0.70:.2f} TL")
    
    # Create optimization problem
    print(f"\n=== CREATING OPTIMIZATION PROBLEM ===")
    prob = LpProblem("ShoppingList", LpMinimize)
    n = len(df)
    print(f"Creating {n} decision variables...")
    
    # Decision variables: number of each item to buy (0-5)
    items = [LpVariable(f"x_{i}", lowBound=0, upBound=5, cat='Integer') for i in range(n)]
    print(f"✅ Created {len(items)} item variables")
    
    # Binary variables for counting different items
    y = [LpVariable(f"y_{i}", cat='Binary') for i in range(n)]
    print(f"✅ Created {len(y)} binary variables")
    
    # Objective: minimize total cost
    print("Setting objective function...")
    prob += lpSum([items[i] * df.iloc[i]["price"] for i in range(n)])
    print("✅ Objective function set")
    
    # Nutrition constraints (scaled for days)
    print("Adding nutrition constraints...")
    prob += lpSum([items[i] * df.iloc[i]["calories"] for i in range(n)]) >= tdee * days
    prob += lpSum([items[i] * df.iloc[i]["protein"] for i in range(n)]) >= protein_g * days
    prob += lpSum([items[i] * df.iloc[i]["fat"] for i in range(n)]) >= fat_g * days
    prob += lpSum([items[i] * df.iloc[i]["carbs"] for i in range(n)]) >= carb_g * days
    print("✅ Nutrition constraints added")
    
    # Budget constraints: use at least 70% of budget
    print("Adding budget constraints...")
    prob += lpSum([items[i] * df.iloc[i]["price"] for i in range(n)]) >= budget * 0.70
    prob += lpSum([items[i] * df.iloc[i]["price"] for i in range(n)]) <= budget
    print("✅ Budget constraints added")
    
    # Category diversity: at least 1 from each main group
    print("Adding category diversity constraints...")
    for group in ['vegetables', 'fruits', 'dairy', 'legumes', 'meat_fish', 'grains']:
        indices = [i for i in range(n) if df.iloc[i]['main_group'] == group]
        if indices:
            prob += lpSum([items[i] for i in indices]) >= 1
            print(f"  ✅ Added constraint for {group} ({len(indices)} products)")
        else:
            print(f"  ⚠️  No products in {group} category - skipping constraint")
    print("✅ Category diversity constraints added")
    
    # Meat/Fish weight constraint: at least 7.5 kg
    print("Adding meat/fish weight constraint...")
    meat_indices = [i for i in range(n) if df.iloc[i]['main_group'] == 'meat_fish']
    if meat_indices:
        prob += lpSum([items[i] * df.iloc[i]["weight_g"] for i in meat_indices]) >= 7500  # 7.5 kg = 7500 g
        print(f"  ✅ Added meat/fish weight constraint (at least 7.5 kg from {len(meat_indices)} products)")
    else:
        print(f"  ⚠️  No meat/fish products available")
    print("✅ Meat/fish weight constraint added")
    
    # Pasta weight constraint: maximum 2.5 kg total
    print("Adding pasta weight constraint...")
    pasta_terms = ['makarna', 'pasta', 'spaghetti', 'penne', 'farfalle', 'rigatoni', 'şehriye', 'erişte']
    pasta_indices = [i for i in range(n) if any(term in df.iloc[i]['name'].lower() for term in pasta_terms)]
    if pasta_indices:
        prob += lpSum([items[i] * df.iloc[i]["weight_g"] for i in pasta_indices]) <= 2500  # 2.5 kg = 2500 g
        print(f"  ✅ Added pasta weight constraint (maximum 2.5 kg from {len(pasta_indices)} products)")
    else:
        print(f"  ⚠️  No pasta products available")
    print("✅ Pasta weight constraint added")
    
    # Bulgur constraints: maximum 2.5 kg total and maximum 3 different items
    print("Adding bulgur constraints...")
    bulgur_terms = ['bulgur', 'bulguru', 'bulgurlu']
    bulgur_indices = [i for i in range(n) if any(term in df.iloc[i]['name'].lower() for term in bulgur_terms)]
    if bulgur_indices:
        # Bulgur weight constraint: maximum 2.5 kg total
        prob += lpSum([items[i] * df.iloc[i]["weight_g"] for i in bulgur_indices]) <= 2500  # 2.5 kg = 2500 g
        # Bulgur variety constraint: maximum 3 different items
        prob += lpSum([y[i] for i in bulgur_indices]) <= 3
        print(f"  ✅ Added bulgur constraints (maximum 2.5 kg and 3 different items from {len(bulgur_indices)} products)")
    else:
        print(f"  ⚠️  No bulgur products available")
    print("✅ Bulgur constraints added")
    
    # Pirinç constraints: maximum 2.5 kg total and maximum 3 different items
    print("Adding pirinç constraints...")
    pirinc_terms = ['pirinç', 'pirinçli', 'rice']
    pirinc_indices = [i for i in range(n) if any(term in df.iloc[i]['name'].lower() for term in pirinc_terms)]
    if pirinc_indices:
        # Pirinç weight constraint: maximum 2.5 kg total
        prob += lpSum([items[i] * df.iloc[i]["weight_g"] for i in pirinc_indices]) <= 2500  # 2.5 kg = 2500 g
        # Pirinç variety constraint: maximum 3 different items
        prob += lpSum([y[i] for i in pirinc_indices]) <= 3
        print(f"  ✅ Added pirinç constraints (maximum 2.5 kg and 3 different items from {len(pirinc_indices)} products)")
    else:
        print(f"  ⚠️  No pirinç products available")
    print("✅ Pirinç constraints added")
    
    # Weight constraint: maximum 50kg total
    print("Adding weight constraint...")
    prob += lpSum([items[i] * df.iloc[i]["weight_g"] for i in range(n)]) <= 50000
    print("✅ Weight constraint added")
    
    # Product count constraint: maximum 200 products total
    print("Adding product count constraint...")
    prob += lpSum([items[i] for i in range(n)]) <= 200
    print("✅ Product count constraint added")
    
    # Product variety constraint: at least 10 different items
    print("Adding product variety constraints...")
    for i in range(n):
        prob += items[i] >= y[i]
    prob += lpSum(y) >= 10
    print("✅ Product variety constraints added")
    
    # Problem statistics
    print(f"\n=== PROBLEM STATISTICS ===")
    print(f"Total variables: {len(prob.variables())}")
    print(f"Total constraints: {len(prob.constraints)}")
    
    # Solve the optimization problem
    print(f"\n=== SOLVING OPTIMIZATION PROBLEM ===")
    print("Starting solver...")
    try:
        prob.solve(PULP_CBC_CMD(msg=True, timeLimit=30))  # 30 second time limit
        print(f"✅ Solver completed with status: {LpStatus[prob.status]}")
    except Exception as e:
        print(f"❌ Solver error: {e}")
        return None
    
    # Check solution status
    if LpStatus[prob.status] != "Optimal":
        print(f"❌ No optimal solution found. Status: {LpStatus[prob.status]}")
        if LpStatus[prob.status] == "Infeasible":
            print("The problem is infeasible - constraints are too strict")
            print("Try relaxing constraints or increasing budget")
        elif LpStatus[prob.status] == "Unbounded":
            print("The problem is unbounded - check objective function")
        elif LpStatus[prob.status] == "Not Solved":
            print("Solver did not complete - may need more time or different approach")
        return None
    
    print("✅ Optimal solution found!")
    
    # Extract results
    print("Extracting results...")
    total_cost = sum([value(items[i]) * df.iloc[i]["price"] for i in range(n)])
    total_weight = sum([value(items[i]) * df.iloc[i]["weight_g"] for i in range(n)])
    total_items = sum([value(items[i]) for i in range(n)])
    
    # Prepare results
    results = {
        'items': [],
        'total_cost': total_cost,
        'total_weight': total_weight,
        'total_items': total_items,
        'budget_usage': (total_cost / budget) * 100
    }
    
    # Collect items that were selected
    selected_count = 0
    for i, var in enumerate(items):
        qty = value(var)
        if qty and qty >= 1:
            selected_count += 1
            item_info = {
                'name': df.iloc[i]['name'],
                'market': df.iloc[i]['market'],
                'quantity': int(qty),
                'price_per_unit': df.iloc[i]['price'],
                'total_price': df.iloc[i]['price'] * qty,
                'weight_per_unit': df.iloc[i]['weight_g'],
                'total_weight': df.iloc[i]['weight_g'] * qty,
                'calories': df.iloc[i]['calories'],
                'protein': df.iloc[i]['protein'],
                'carbs': df.iloc[i]['carbs'],
                'fat': df.iloc[i]['fat'],
                'category': df.iloc[i]['main_group']
            }
            results['items'].append(item_info)
    
    print(f"✅ Results extracted: {selected_count} different products selected")
    return results

# --- Display Results ---
def display_results(results, budget, tdee, protein_g, fat_g, carb_g, days):
    if results is None:
        return
    
    print("\n" + "="*60)
    print("🎯 RECOMMENDED SHOPPING LIST")
    print("="*60)
    
    # Display all items as a single list
    for item in results['items']:
        print(f"• {item['name']} ({item['market']})")
        print(f"  {item['quantity']} adet - {item['total_price']:.2f} TL, {item['total_weight']/1000:.2f} kg")
    
    # Summary
    print("\n" + "="*60)
    print("📊 SHOPPING SUMMARY")
    print("="*60)
    print(f"💰 Total Cost: {results['total_cost']:.2f} TL ({results['budget_usage']:.1f}% of budget)")
    print(f"⚖️  Total Weight: {results['total_weight']/1000:.2f} kg")
    print(f"📦 Total Items: {int(results['total_items'])}")
    print(f"🛒 Different Products: {len(results['items'])}")
    
    # Nutrition summary
    total_calories = sum([item['calories'] * item['quantity'] for item in results['items']])
    total_protein = sum([item['protein'] * item['quantity'] for item in results['items']])
    total_fat = sum([item['fat'] * item['quantity'] for item in results['items']])
    total_carbs = sum([item['carbs'] * item['quantity'] for item in results['items']])
    
    print(f"\n🍎 NUTRITION SUMMARY (for {days} days):")
    print(f"  Calories: {total_calories:.0f} kcal (target: {tdee*days:.0f} kcal)")
    print(f"  Protein: {total_protein:.0f} g (target: {protein_g*days:.0f} g)")
    print(f"  Fat: {total_fat:.0f} g (target: {fat_g*days:.0f} g)")
    print(f"  Carbs: {total_carbs:.0f} g (target: {carb_g*days:.0f} g)")

# --- Save Results to File ---
def save_results_to_file(results, budget, tdee, protein_g, fat_g, carb_g, days):
    if results is None:
        return
    
    # Delete existing file if it exists
    if os.path.exists("shopping_output.txt"):
        os.remove("shopping_output.txt")
    
    with open("shopping_output.txt", "w", encoding="utf-8") as f:
        f.write("🎯 RECOMMENDED SHOPPING LIST\n")
        f.write("="*60 + "\n\n")
        
        # Write all items as a single list
        for item in results['items']:
            f.write(f"• {item['name']} ({item['market']})\n")
            f.write(f"  {item['quantity']} adet - {item['total_price']:.2f} TL, {item['total_weight']/1000:.2f} kg\n")
        f.write("\n")
        
        # Summary
        f.write("="*60 + "\n")
        f.write("📊 SHOPPING SUMMARY\n")
        f.write("="*60 + "\n")
        f.write(f"💰 Total Cost: {results['total_cost']:.2f} TL ({results['budget_usage']:.1f}% of budget)\n")
        f.write(f"⚖️  Total Weight: {results['total_weight']/1000:.2f} kg\n")
        f.write(f"📦 Total Items: {int(results['total_items'])}\n")
        f.write(f"🛒 Different Products: {len(results['items'])}\n")
        
        # Nutrition summary
        total_calories = sum([item['calories'] * item['quantity'] for item in results['items']])
        total_protein = sum([item['protein'] * item['quantity'] for item in results['items']])
        total_fat = sum([item['fat'] * item['quantity'] for item in results['items']])
        total_carbs = sum([item['carbs'] * item['quantity'] for item in results['items']])
        
        f.write(f"\n🍎 NUTRITION SUMMARY (for {days} days):\n")
        f.write(f"  Calories: {total_calories:.0f} kcal (target: {tdee*days:.0f} kcal)\n")
        f.write(f"  Protein: {total_protein:.0f} g (target: {protein_g*days:.0f} g)\n")
        f.write(f"  Fat: {total_fat:.0f} g (target: {fat_g*days:.0f} g)\n")
        f.write(f"  Carbs: {total_carbs:.0f} g (target: {carb_g*days:.0f} g)\n")
    
    print("💾 Results saved to shopping_output.txt")

# --- Main Function ---
def main():
    print("🚀 Starting Shopping Optimizer v2.0")
    
    # Load and preprocess data
    print("\n📂 Loading data...")
    df = pd.read_csv("enriched_2025_05_21.csv")
    df = preprocess_data(df)
    
    # Get user inputs
    age, gender, weight, height, activity, goal, budget = get_user_input()
    days = 30  # Fixed at 30 days
    
    # Calculate nutrition targets
    tdee = calculate_tdee(age, gender, weight, height, activity)
    tdee, protein_g, fat_g, carb_g = get_macro_targets(tdee, goal)
    
    print(f"\n🎯 TARGET NUTRITION (for {days} days):")
    print(f"  Calories: {tdee*days:.0f} kcal")
    print(f"  Protein: {protein_g*days:.0f} g")
    print(f"  Fat: {fat_g*days:.0f} g")
    print(f"  Carbs: {carb_g*days:.0f} g")
    
    # Run optimization
    results = optimize_shopping(df, tdee, protein_g, fat_g, carb_g, budget, days)
    
    # Display and save results
    display_results(results, budget, tdee, protein_g, fat_g, carb_g, days)
    save_results_to_file(results, budget, tdee, protein_g, fat_g, carb_g, days)

if __name__ == "__main__":
    main() 