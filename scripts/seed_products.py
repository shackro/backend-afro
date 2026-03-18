#!/usr/bin/env python
"""
Script to seed products with KES and USD prices.
Run with: python manage.py shell < scripts/seed_products.py
"""

import os
import sys
import django
import random
from decimal import Decimal

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afroconnect.settings')
django.setup()

from apps.products.models import Product
from apps.accounts.models import User

# Exchange rate (1 USD = 130 KES)
USD_TO_KES = 130


def generate_product_name(index, category):
    """Generate product name based on category"""
    prefixes = ['Essential', 'Growth', 'Premium', 'Elite', 'Ultimate', 'Pro', 'Max', 'Plus']
    suffixes = ['Plan', 'Package', 'Strategy', 'Portfolio', 'Fund', 'Trust', 'Venture']

    if category == 'starter':
        return f"KES Starter {random.choice(suffixes)}"
    elif category == 'growth':
        return f"KES Growth {random.choice(suffixes)}"
    elif category == 'premium':
        return f"KES Premium {random.choice(suffixes)}"
    else:
        return f"KES {random.choice(prefixes)} {random.choice(suffixes)}"


def calculate_returns(price_kes):
    """Calculate realistic returns based on price"""
    # Daily return rate between 0.5% and 1.5%
    daily_rate = Decimal(str(random.uniform(0.005, 0.015))).quantize(Decimal('0.0001'))

    # Duration between 20-40 days
    duration = random.randint(20, 40)

    # Calculate daily income
    daily_income_kes = (price_kes * daily_rate).quantize(Decimal('0.01'))
    daily_income_usd = (daily_income_kes / USD_TO_KES).quantize(Decimal('0.01'))

    # Calculate commissions
    b_commission_kes = (daily_income_kes * Decimal('0.10')).quantize(Decimal('0.01'))  # 10%
    c_commission_kes = (daily_income_kes * Decimal('0.06')).quantize(Decimal('0.01'))  # 6%
    d_commission_kes = (daily_income_kes * Decimal('0.03')).quantize(Decimal('0.01'))  # 3%

    return {
        'daily_income_kes': daily_income_kes,
        'daily_income_usd': daily_income_usd,
        'duration': duration,
        'b_commission_kes': b_commission_kes,
        'c_commission_kes': c_commission_kes,
        'd_commission_kes': d_commission_kes,
        'daily_rate': daily_rate * 100,  # Convert to percentage
    }


def seed_products():
    """Main seeding function"""
    print("🌱 Seeding KES-based products...")

    # Clear existing products (optional - comment out if you want to keep existing)
    # Product.objects.all().delete()
    # print("🗑️ Cleared existing products")

    products_created = 0

    # Generate 20 products with prices between 5,000 and 12,000 KES
    for i in range(20):
        # Generate random KES price between 5,000 and 12,000
        price_kes = Decimal(str(random.randint(5000, 12000))).quantize(Decimal('0.01'))

        # Calculate USD equivalent
        price_usd = (price_kes / USD_TO_KES).quantize(Decimal('0.01'))

        # Determine category based on price
        if price_kes < 7000:
            category = 'starter'
            risk_level = 'Low'
        elif price_kes < 9000:
            category = 'growth'
            risk_level = 'Moderate'
        else:
            category = 'premium'
            risk_level = 'High'

        # Calculate returns
        returns = calculate_returns(price_kes)

        # Create product name
        name = generate_product_name(i, category)

        # Create description
        description = f"""🚀 {name}

💎 Investment Amount: KES {price_kes:,.0f} (${price_usd:,.0f})
📈 Daily Return: {returns['daily_rate']:.2f}%
💰 Daily Income: KES {returns['daily_income_kes']:,.0f} (${returns['daily_income_usd']:,.0f})
⏱️ Duration: {returns['duration']} days
📊 Total Return: KES {(returns['daily_income_kes'] * returns['duration']):,.0f}

🎯 Commission Structure:
• Level 1 (Direct Referral - 10%): KES {returns['b_commission_kes']:,.0f}
• Level 2 (6%): KES {returns['c_commission_kes']:,.0f}
• Level 3 (3%): KES {returns['d_commission_kes']:,.0f}

📋 Risk Level: {risk_level}
🌍 Base Currency: USD (1 USD = {USD_TO_KES} KES)

Start your investment journey with {name} today!"""

        # Create the product (store in USD as base currency)
        product = Product.objects.create(
            name=name,
            price=price_usd,  # Store in USD
            daily_income=returns['daily_income_usd'],
            validity_period=returns['duration'],
            b_commission=returns['b_commission_kes'] / USD_TO_KES,  # Convert to USD
            c_commission=returns['c_commission_kes'] / USD_TO_KES,  # Convert to USD
            d_commission=returns['d_commission_kes'] / USD_TO_KES,  # Convert to USD
            description=description,
            min_investment=price_usd,
            max_investment=price_usd * 3,  # Allow up to 3x the base price
            is_active=True,
        )

        products_created += 1
        print(
            f"✅ Created: {name} - KES {price_kes:,.0f} (${price_usd:,.0f}) - {returns['duration']} days - {returns['daily_rate']:.2f}% daily")

    print(f"\n🎉 Successfully created {products_created} KES-based products!")
    print("\n📊 Summary:")
    print(f"   • Price Range: KES 5,000 - 12,000 (${(5000 / USD_TO_KES):.0f} - ${(12000 / USD_TO_KES):.0f})")
    print(f"   • Daily Returns: 0.5% - 1.5%")
    print(f"   • Durations: 20-40 days")
    print(f"   • Exchange Rate: 1 USD = {USD_TO_KES} KES")


if __name__ == "__main__":
    seed_products()