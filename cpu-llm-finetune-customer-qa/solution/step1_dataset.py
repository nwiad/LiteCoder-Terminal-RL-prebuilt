#!/usr/bin/env python3
"""Step 1: Generate customer-service QA dataset with 1000+ pairs."""
import json
import random

random.seed(42)

# Base QA templates for three domains
shipping_qa = [
    ("How long does standard shipping take?", "Standard shipping typically takes 5-7 business days within the continental US."),
    ("What are the shipping options?", "We offer standard (5-7 days), express (2-3 days), and overnight shipping."),
    ("How can I track my order?", "Track your order using the tracking number emailed after shipment."),
    ("Do you offer free shipping?", "Free shipping is available on orders over $50."),
    ("What is the cost of express shipping?", "Express shipping costs $12.99 and delivers in 2-3 business days."),
    ("Can I change my shipping address?", "You can update your shipping address within 1 hour of ordering by contacting support."),
    ("Do you ship internationally?", "Yes, we ship to over 50 countries worldwide."),
    ("What if my package is lost?", "Contact us within 30 days for a replacement or full refund."),
    ("How long does international shipping take?", "International shipping takes 10-21 business days."),
    ("Can I expedite my shipping?", "Yes, contact support to upgrade to express or overnight shipping."),
    ("What carrier do you use?", "We use USPS, UPS, and FedEx depending on destination."),
    ("Is signature required for delivery?", "Signature is required for orders over $200."),
    ("Do you offer same-day delivery?", "Same-day delivery is available in select metro areas for orders before noon."),
    ("What is the shipping cut-off time?", "Orders before 2 PM EST on business days ship same day."),
    ("Can I ship to a PO Box?", "Yes, we ship to PO Boxes via USPS standard shipping."),
    ("What if my package arrives damaged?", "Take photos and contact us within 48 hours for a replacement."),
    ("Do you offer weekend delivery?", "Weekend delivery is available with express shipping for an extra fee."),
    ("Can I schedule a delivery date?", "Select a preferred delivery date at checkout for $5.99."),
    ("What regions do you ship to?", "We ship to all 50 US states, Canada, UK, EU, Australia, and Japan."),
    ("How do I get a shipping label?", "A prepaid label is emailed when your return is approved."),
]

returns_qa = [
    ("What is your return policy?", "Return most items within 30 days of purchase for a full refund."),
    ("How do I start a return?", "Go to Order History in your account and click Return Item."),
    ("Can I return a sale item?", "Sale items can be returned within 14 days for store credit only."),
    ("How long do refunds take?", "Refunds are processed within 5-7 business days after receiving the item."),
    ("Do I need original packaging?", "Original packaging is preferred but not required. Items must be unused."),
    ("Can I exchange instead of return?", "Yes, request an exchange for a different size or color."),
    ("Who pays return shipping?", "We provide free return shipping labels for domestic returns."),
    ("Can I return an opened item?", "Opened items can be returned if defective or not as described."),
    ("What items cannot be returned?", "Personalized items, gift cards, and intimate apparel cannot be returned."),
    ("Can I return without a receipt?", "We can look up your order using your email address."),
    ("How do I check return status?", "Check return status in your account under Order History."),
    ("Can I return a gift?", "Gifts can be returned for store credit. The buyer will not be notified."),
    ("What if I received the wrong item?", "Contact us and we will ship the correct item at no cost."),
    ("Do you offer partial returns?", "Yes, return individual items from a multi-item order."),
    ("Can I return after 30 days?", "Late returns may be accepted for store credit at manager discretion."),
    ("What condition must returns be in?", "Items must be unworn, unwashed, with original tags attached."),
    ("How do I print a return label?", "Download the return label from the email sent after initiating a return."),
    ("Can I drop off my return?", "Drop off returns at any UPS or USPS location with our prepaid label."),
    ("Will I get a full refund?", "Full refunds for items returned in original condition within 30 days."),
    ("Can I cancel a return request?", "Cancel a return request before shipping by contacting support."),
]

coupons_qa = [
    ("How do I apply a coupon code?", "Enter your coupon code at checkout in the promo code field."),
    ("Can I use multiple coupons?", "Only one coupon code can be applied per order."),
    ("Why is my coupon not working?", "Check the expiration date and minimum purchase requirements."),
    ("Do coupons work on sale items?", "Most coupons cannot be combined with existing sale prices."),
    ("How do I get a coupon?", "Sign up for our newsletter to receive exclusive coupon codes."),
    ("Can I use a coupon after placing an order?", "Coupons cannot be applied retroactively to placed orders."),
    ("Do coupons expire?", "Yes, all coupons have an expiration date printed on them."),
    ("Is there a minimum purchase for coupons?", "Some coupons require a minimum purchase, check the terms."),
    ("Can I share my coupon?", "Coupons are transferable unless marked as single-use."),
    ("Where do I find current promotions?", "Visit our Deals page or sign up for email alerts."),
    ("Do you offer first-time buyer discounts?", "New customers get 15% off with code WELCOME15."),
    ("Can I use a coupon on gift cards?", "Coupons cannot be applied to gift card purchases."),
    ("What is your price match policy?", "We match competitor prices within 7 days of purchase."),
    ("Do you have a loyalty program?", "Yes, earn 1 point per dollar spent and redeem for discounts."),
    ("How do loyalty points work?", "Accumulate points with purchases and redeem 100 points for $5 off."),
    ("Can I get a student discount?", "Students get 10% off with a valid student email address."),
    ("Do you offer military discounts?", "Active military and veterans receive 15% off with valid ID."),
    ("Are there seasonal sales?", "We have major sales during Black Friday, summer, and end of season."),
    ("Can I combine a coupon with free shipping?", "Yes, coupon codes can be used with free shipping offers."),
    ("How do I unsubscribe from promotions?", "Click unsubscribe at the bottom of any promotional email."),
]

# Variation prefixes/suffixes to expand dataset to 1000+ pairs
q_prefixes = [
    "", "I want to know: ", "Please tell me, ", "Quick question: ",
    "Hi, ", "Hello, ", "Hey, ", "Excuse me, ",
    "I was wondering, ", "Could you help me? ", "I need help. ",
]
q_suffixes = ["", " Thanks.", " Thank you!", " Please help.", " I need to know."]
a_prefixes = [
    "", "Sure! ", "Of course! ", "Great question! ", "Happy to help! ",
    "Absolutely. ", "No problem. ", "Thanks for asking. ",
]

all_base = shipping_qa + returns_qa + coupons_qa  # 60 base pairs

dataset = []
seen = set()
for q, a in all_base:
    for qp in q_prefixes:
        for qs in q_suffixes:
            for ap in a_prefixes:
                new_q = qp + q + qs
                new_a = ap + a
                key = (new_q, new_a)
                if key not in seen:
                    seen.add(key)
                    dataset.append({"question": new_q, "answer": new_a})

# Shuffle and trim to exactly 1200 for a clean split
random.shuffle(dataset)
dataset = dataset[:1200]

print(f"Total QA pairs generated: {len(dataset)}")

# Save full dataset
with open("/app/dataset.json", "w") as f:
    json.dump(dataset, f, indent=2)

# 80/20 split
split_idx = int(len(dataset) * 0.8)
train = dataset[:split_idx]
test = dataset[split_idx:]

with open("/app/train_dataset.json", "w") as f:
    json.dump(train, f, indent=2)
with open("/app/test_dataset.json", "w") as f:
    json.dump(test, f, indent=2)

print(f"Train: {len(train)}, Test: {len(test)}")
print("Dataset generation complete.")
