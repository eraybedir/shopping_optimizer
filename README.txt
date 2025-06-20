Shopping Optimizer Project v2.0
==============================

This project generates an optimal 30-day shopping list based on nutritional needs and various constraints, using linear programming optimization with PuLP and CBC solver.

Setup
-----
1. Make sure you have Python 3.7+ installed
2. Install the required packages:
   pip install -r requirements.txt
3. Place the product data file (enriched_2025_05_21.csv) in the same directory
4. Run the program:
   python shopping_optimizer_v2.py

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

2. Budget Constraints:
   - Must use at least 70% of the provided budget
   - Cannot exceed the total budget

3. Category Diversity:
   - At least one item from each main food group:
     * Vegetables
     * Fruits
     * Dairy
     * Legumes
     * Meat/Fish
     * Grains

4. Product Exclusions:
   - Granola products
   - Noodle products
   - Liver/heart products
   - Products containing Turkish words "çabuk" or "bardak"
   - Products containing "pilavı" (rice dishes)
   - Products containing "çikolata" (chocolate)

5. Weight Constraints:
   - Maximum total weight: 50kg
   - Maximum 200 total items
   - Minimum 10 different products

6. Specific Product Constraints:
   - Pasta: Maximum 2.5 kg total
   - Bulgur: Maximum 2.5 kg total, maximum 3 different items
   - Pirinç (Rice): Maximum 2.5 kg total, maximum 3 different items
   - Meat/Fish: Minimum 7.5 kg total

7. Data Quality:
   - Excludes items with missing or invalid prices
   - Excludes items with missing or negative nutritional values
   - Excludes items with missing weight information

Output Format
------------
The program prints:
1. Target nutritional values for 30 days
2. Optimization progress and statistics
3. Recommended shopping list with:
   - Product names and markets
   - Quantities
   - Prices
   - Weights
4. Total cost, weight, and item count
5. Nutrition summary comparison with targets

Files
-----
- shopping_optimizer_v2.py: Main program file (latest version)
- shopping_optimizer.py: Original version
- requirements.txt: Python package dependencies
- enriched_2025_05_21.csv: Product database with nutritional information
- shopping_output.txt: Latest optimization results

Technical Details
----------------
- Uses PuLP library for linear programming
- CBC solver for optimization (free and efficient)
- 30-second time limit for optimization
- Handles 11,000+ products efficiently
- Case-insensitive product matching
- Automatic weight extraction from product names

Notes
-----
- The program automatically maps products to main food categories based on their names
- All nutritional calculations are done on a per-item basis
- The optimization prioritizes cost minimization while meeting all constraints
- Results are saved to shopping_output.txt for easy reference
- The solver uses a 30-second time limit to ensure reasonable response times 