SEGMENT_RECOMMENDATIONS = {
    "VIP Customer": {
        "headline": "Protect and reward this relationship",
        "actions": [
            "Offer exclusive early access to new products or services",
            "Assign a dedicated point of contact for priority support",
            "Send personalized thank-you offers tied to their purchase history"
        ]
    },
    "Loyal Customer": {
        "headline": "Deepen loyalty before they drift",
        "actions": [
            "Enroll in a loyalty or rewards program if one exists",
            "Send periodic check-ins or satisfaction surveys",
            "Offer bundle discounts on frequently purchased items"
        ]
    },
    "Regular Customer": {
        "headline": "Grow engagement and purchase frequency",
        "actions": [
            "Send targeted upsell offers based on past purchases",
            "Introduce them to related products or services",
            "Use email or SMS reminders to encourage repeat visits"
        ]
    },
    "At-Risk Customer": {
        "headline": "Act now before this customer churns",
        "actions": [
            "Send a win-back discount or limited-time offer",
            "Reach out directly to ask about their experience",
            "Highlight new products or improvements since their last purchase"
        ]
    }
}


def get_recommendation(segment_name):
    return SEGMENT_RECOMMENDATIONS.get(segment_name, {
        "headline": "No specific guidance available",
        "actions": []
    })