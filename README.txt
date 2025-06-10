Shopping Optimizer Project
=========================

This project generates an optimal 30-day shopping list based on nutritional needs and various constraints, using linear programming optimization.

Setup
-----
1. Make sure you have Python 3 installed
2. Install the required packages:
   pip install -r requirements.txt
3. Place the product data file (enriched_2025_05_21.csv) in the same directory
4. Run the program:
   python shopping_optimizer.py

How It Works
-----------
The program uses linear programming to find the optimal combination of products that:
1. Meets daily nutritional requirements (calories, protein, fat, carbs)
2. Minimizes total cost
3. Satisfies all constraints (see below)

User Input Parameters
-------------------
The program will ask for:
1. Age (years)
2. Gender (male/female)
3. Weight (kg)
4. Height (cm)
5. Activity Level (options):
   - sedentary
   - lightly active
   - moderately active
   - very active
   - extra active
6. Goal (options):
   - gaining weight
   - doing sports
   - losing weight
   - being healthy
7. Monthly budget (TL)

Constraints
----------
1. Nutritional Requirements:
   - Calories, protein, fat, and carbs based on TDEE calculation
   - Adjusts for activity level and health goals

2. Category Diversity:
   - At least one item from each main food group:
     * Vegetables
     * Fruits
     * Dairy
     * Legumes
     * Meat/Fish
     * Grains

3. Item Quantity Limits:
   - Maximum 5 units of any single item
   - Minimum 15 different items in total
   - All quantities must be whole numbers (no fractional items)

4. Weight Constraints:
   - Maximum total weight: 50kg
   - Individual items over 5kg are excluded

5. Data Quality:
   - Excludes items with:
     * Missing prices
     * Negative prices
     * Missing nutritional values
     * Negative nutritional values

6. Category Exclusions:
   - All beverages are excluded
   - Focus on solid foods only

Output Format
------------
The program prints:
1. Target nutritional values for 30 days
2. Recommended shopping list with:
   - Product names
   - Quantities
   - Prices
   - Weights
3. Total cost and weight

Files
-----
- shopping_optimizer.py: Main program file
- requirements.txt: Python package dependencies
- enriched_2025_05_21.csv: Product database with nutritional information

Notes
-----
- The program automatically maps products to main food categories based on their names and subcategories
- All nutritional calculations are done on a per-item basis
- The optimization prioritizes cost minimization while meeting all constraints 