from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
import os
import re

def categorize_expense_with_llm(merchant: str, amount: float, category_hint: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "test_key":
        # Fallback for dev mode without real key
        return "Other / Uncategorized"
    
    llm = ChatGroq(
        model="llama3-70b-8192",
        temperature=0.0,
        api_key=api_key
    )
    
    prompt = PromptTemplate(
        input_variables=["merchant", "amount", "hint"],
        template=(
            "You are an expense categorization assistant. Categorize the following expense into EXACTLY ONE of these 5 categories:\n"
            "- Airfare\n"
            "- Lodging\n"
            "- Meals\n"
            "- Ground Transport\n"
            "- Other / Uncategorized\n\n"
            "Merchant: {merchant}\n"
            "Amount: {amount}\n"
            "Category Hint: {hint}\n\n"
            "Only output the category name. If you are not completely sure, output 'Other / Uncategorized'."
        )
    )
    
    try:
        chain = prompt | llm
        result = chain.invoke({"merchant": merchant, "amount": amount, "hint": category_hint})
        content = result.content.strip()
        # Clean markdown if present
        content = re.sub(r'```.*?```', '', content, flags=re.DOTALL).strip()
        valid_categories = ["Airfare", "Lodging", "Meals", "Ground Transport", "Other / Uncategorized"]
        for vc in valid_categories:
            if vc.lower() in content.lower():
                return vc
        return "Other / Uncategorized"
    except Exception as e:
        print(f"LLM Categorization failed: {e}")
        return "Other / Uncategorized"
