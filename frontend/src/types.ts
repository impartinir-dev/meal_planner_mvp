export type User = {
  id: number
  email: string
  is_admin: boolean
  is_pro: boolean
}

export type Store = { id: string; name: string; badge: string; logo_char: string }
export type Diet = { id: string; name: string; icon: string; desc: string }
export type PantryStaple = { name: string; icon: string; hint: string }

export type Meta = {
  stores: Store[]
  diets: Diet[]
  pantry_staples: PantryStaple[]
  allergens: { id: string; name: string }[]
  ingredients: string[]
  deal_week: string
  version: string
  pro_price: number
  pro_period: string
  calories_range: { min: number; max: number; step: number }
  protein_range: { min: number; max: number; step: number }
  budget_range: { min: number; max: number; step: number }
  activity_levels?: { id: string; name: string }[]
  goals?: { id: string; name: string }[]
}

export type Ingredient = {
  name: string
  quantity: number
  unit: string
  is_deal: boolean
  deal_badge: string | null
  in_pantry: boolean
  item_cost: number
  aisle: string
}

export type Meal = {
  id: string
  name: string
  category: string
  prep_time: string
  lucide_icon: string
  cost: number
  regular_cost: number
  deal_savings: number
  has_deal: boolean
  macros: { calories: number; protein: number; carbs: number; fat: number }
  ingredients: Ingredient[]
  instructions: string | string[]
  locked?: boolean
  status?: 'cooked' | 'skipped' | null
}

export type ShoppingItem = {
  name: string
  quantity: number
  unit: string
  packs: number
  pack_size: number
  pack_unit: string
  is_deal: boolean
  deal_badge: string | null
  cost: number
  aisle: string
  in_pantry?: boolean
}

export type Plan = {
  status: string
  store: string
  diet: string
  days: number
  budget: number
  portions: number
  target_calories: number
  target_protein: number
  deal_week: string
  total_cost: number
  regular_cost: number
  deal_savings: number
  pantry_savings: number
  combined_savings: number
  budget_percent: number
  over_budget: boolean
  relaxations: string[]
  daily_avg: { calories: number; protein: number; carbs: number; fat: number }
  days_plan: {
    day_index: number
    day_name: string
    cost: number
    calories: number
    protein: number
    meals: Meal[]
  }[]
  shopping_list: {
    to_buy: { aisle: string; items: ShoppingItem[] }[]
    already_at_home: ShoppingItem[]
    pack_cost: number
  }
  pantry_items: string[]
  exclude?: string[]
  members?: HouseholdMember[]
  recipe_cost?: number
  checkout_cost?: number
}

export type HouseholdMember = {
  id: string
  name: string
  calories: number
  protein: number
}

export type Prefs = {
  store: string
  diet: string
  budget: number
  days: number
  calories: number
  protein: number
  pantry: string[]
  portions: number
  exclude: string[]
  members: HouseholdMember[]
}

export type PlanPayload = {
  prefs: Prefs
  plan: Plan
  updated_at: string | null
}
