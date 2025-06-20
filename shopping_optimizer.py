import pandas as pd
from pulp import LpProblem, LpVariable, lpSum, LpMinimize, LpStatus, value
from pulp import PULP_CBC_CMD
import re
import os

# --- Category Mapping ---
def map_main_group(row):
    subcat = str(row['subcategory']).lower()
    name = str(row['name']).lower()
    # Vegetables
    if 'sebze' in subcat or 'domates' in name or 'biber' in name or 'salatalık' in name or 'patates' in name:
        return 'vegetables'
    # Fruits
    if 'meyve' in subcat or 'elma' in name or 'muz' in name or 'portakal' in name or 'armut' in name:
        return 'fruits'
    # Dairy
    if 'süt' in subcat or 'kahvalt' in subcat or 'peynir' in name or 'yoğurt' in name:
        return 'dairy'
    # Legumes
    if 'bakliyat' in subcat or 'fasulye' in name or 'mercimek' in name or 'nohut' in name:
        return 'legumes'
    # Meat/Fish
    if 'et' in subcat or 'balık' in subcat or 'tavuk' in subcat:
        return 'meat_fish'
    # Grains
    if 'temel gıda' in subcat or 'ekmek' in name or 'bulgur' in name or 'pirinç' in name or 'makarna' in name:
        return 'grains'
    return 'other'

def get_user_input():
    print("\nPlease enter your information:")
    while True:
        try:
            age = int(input("Age: "))
            if 0 < age < 120:
                break
            print("Please enter a valid age between 1 and 120.")
        except ValueError:
            print("Please enter a valid number for age.")

    while True:
        gender = input("Gender (male/female): ").strip().lower()
        if gender in ['male', 'female']:
            break
        print("Please enter either 'male' or 'female'.")

    while True:
        try:
            weight = float(input("Weight (kg): "))
            if 20 < weight < 300:
                break
            print("Please enter a valid weight between 20 and 300 kg.")
        except ValueError:
            print("Please enter a valid number for weight.")

    while True:
        try:
            height = float(input("Height (cm): "))
            if 100 < height < 250:
                break
            print("Please enter a valid height between 100 and 250 cm.")
        except ValueError:
            print("Please enter a valid number for height.")

    while True:
        activity = input("Activity level (sedentary/lightly active/moderately active/very active/extra active): ").strip().lower()
        if activity in ['sedentary', 'lightly active', 'moderately active', 'very active', 'extra active']:
            break
        print("Please enter one of the valid activity levels.")

    while True:
        goal = input("Goal (gaining weight/doing sports/losing weight/being healthy): ").strip().lower()
        if goal in ['gaining weight', 'doing sports', 'losing weight', 'being healthy']:
            break
        print("Please enter one of the valid goals.")

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
    if gender == "male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
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
    if "gain" in goal:
        tdee += 200
    elif "lose" in goal:
        tdee -= 200
    if "sport" in goal:
        protein_ratio = 0.20
        fat_ratio = 0.25
        carb_ratio = 0.55
    else:
        protein_ratio = 0.15
        fat_ratio = 0.25
        carb_ratio = 0.60
    protein_g = (tdee * protein_ratio) / 4
    fat_g = (tdee * fat_ratio) / 9
    carb_g = (tdee * carb_ratio) / 4
    return tdee, protein_g, fat_g, carb_g

def extract_weight(name):
    match = re.search(r"(\d+[.,]?\d*)\s*(kg|g|gr)", name.lower())
    if match:
        value = float(match.group(1).replace(",", "."))
        unit = match.group(2)
        if "kg" in unit:
            return int(value * 1000)
        else:
            return int(value)
    return 1000

# --- Optimization ---
def optimize_shopping(df, tdee, protein_g, fat_g, carb_g, budget, days=30):
    print(f"\nOptimization parameters:")
    print(f"Budget: {budget} TL")
    print(f"Required calories: {tdee * days:.0f} kcal")
    print(f"Required protein: {protein_g * days:.0f} g")
    print(f"Required fat: {fat_g * days:.0f} g")
    print(f"Required carbs: {carb_g * days:.0f} g")
    print(f"Available products: {len(df)}")
    
    prob = LpProblem("ShoppingList", LpMinimize)
    n = len(df)
    # Integer variables: number of items to buy (max 5)
    items = [LpVariable(f"x_{i}", lowBound=0, upBound=5, cat='Integer') for i in range(n)]
    # Objective: minimize total cost
    prob += lpSum([items[i] * df.iloc[i]["price"] for i in range(n)])
    # Nutrition constraints (scaled for days)
    prob += lpSum([items[i] * df.iloc[i]["calories"] for i in range(n)]) >= tdee * days
    prob += lpSum([items[i] * df.iloc[i]["protein"] for i in range(n)]) >= protein_g * days
    prob += lpSum([items[i] * df.iloc[i]["fat"] for i in range(n)]) >= fat_g * days
    prob += lpSum([items[i] * df.iloc[i]["carbs"] for i in range(n)]) >= carb_g * days
    # Budget constraint: use at least 70% of budget
    prob += lpSum([items[i] * df.iloc[i]["price"] for i in range(n)]) >= budget * 0.70
    prob += lpSum([items[i] * df.iloc[i]["price"] for i in range(n)]) <= budget
    # Category diversity: at least 1 from each main group
    for group in ['vegetables', 'fruits', 'dairy', 'legumes', 'meat_fish', 'grains']:
        indices = [i for i in range(n) if df.iloc[i]['main_group'] == group]
        if indices:
            prob += lpSum([items[i] for i in indices]) >= 1
    # Maximum total weight: 50kg
    prob += lpSum([items[i] * df.iloc[i]["weight_g"] for i in range(n)]) <= 50000
    # Maximum 200 products total
    prob += lpSum([items[i] for i in range(n)]) <= 200
    # At least 10 different items
    y = [LpVariable(f"y_{i}", cat='Binary') for i in range(n)]
    for i in range(n):
        prob += items[i] >= y[i]
    prob += lpSum(y) >= 10
    prob.solve(PULP_CBC_CMD(msg=False))
    if LpStatus[prob.status] != "Optimal":
        print("No feasible shopping list found within budget and constraints.")
        return
    total_cost = sum([value(items[i]) * df.iloc[i]["price"] for i in range(n)])
    total_weight = sum([value(items[i]) * df.iloc[i]["weight_g"] for i in range(n)])
    total_items = sum([value(items[i]) for i in range(n)])
    print("\nRecommended Shopping List:")
    for i, var in enumerate(items):
        qty = value(var)
        if qty and qty >= 1:
            print(f"{df.iloc[i]['name']} ({df.iloc[i]['market']}): {int(qty)} adet - {df.iloc[i]['price']*qty:.2f} TL, {df.iloc[i]['weight_g']*qty/1000:.2f} kg")
    print(f"\nTotal cost: {total_cost:.2f} TL ({total_cost/budget*100:.1f}% of budget)")
    print(f"Total weight: {total_weight/1000:.2f} kg")
    print(f"Total items: {int(total_items)}")

# --- Main ---
def main():
    # Read CSV
    df = pd.read_csv("enriched_2025_05_21.csv")
    # Data quality: drop missing/negative price or nutrition
    df["price"] = df["price"].astype(str).str.replace(" TL", "", regex=False).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    for col in ["calories", "protein", "carbs", "fat"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["price", "calories", "protein", "carbs", "fat"])
    df = df[(df["price"] > 0) & (df["calories"] >= 0) & (df["protein"] >= 0) & (df["carbs"] >= 0) & (df["fat"] >= 0)]
    # Exclude beverages
    df = df[~df["category"].str.lower().str.contains("içecek")]
    # Extract item weight in grams
    df["weight_g"] = df["name"].apply(extract_weight)
    # Exclude items > 5kg
    df = df[df["weight_g"] <= 5000]
    # Map to main food groups
    df['main_group'] = df.apply(map_main_group, axis=1)
    
    # Filter out very expensive items (over 1000 TL)
    df = df[df['price'] <= 1000]
    
    # Filter out products with zero calories
    df = df[df['calories'] > 0]
    
    print(f"Data loaded: {len(df)} products available")
    print(f"Price range: {df['price'].min():.2f} - {df['price'].max():.2f} TL")
    print(f"Calories range: {df['calories'].min():.0f} - {df['calories'].max():.0f} kcal")
    print(f"Average price: {df['price'].mean():.2f} TL")
    print(f"Average calories: {df['calories'].mean():.0f} kcal")
    
    # Get user inputs
    age, gender, weight, height, activity, goal, budget = get_user_input()
    days = 30  # Fixed at 30 days
    
    tdee = calculate_tdee(age, gender, weight, height, activity)
    tdee, protein_g, fat_g, carb_g = get_macro_targets(tdee, goal)
    output_lines = []
    output_lines.append(f"Target Calories: {tdee*days:.0f} kcal, Protein: {protein_g*days:.0f}g, Fat: {fat_g*days:.0f}g, Carbs: {carb_g*days:.0f}g (for {days} days)\n")
    
    # Capture the print output of optimize_shopping
    import io
    import sys
    buffer = io.StringIO()
    sys_stdout = sys.stdout
    sys.stdout = buffer
    optimize_shopping(df, tdee, protein_g, fat_g, carb_g, budget, days=days)
    sys.stdout = sys_stdout
    output_lines.append(buffer.getvalue())
    
    # Delete existing file if it exists
    if os.path.exists("shopping_output.txt"):
        os.remove("shopping_output.txt")
    
    with open("shopping_output.txt", "w", encoding="utf-8") as f:
        f.writelines(output_lines)
    print("Results saved to shopping_output.txt")

if __name__ == "__main__":
    main() 