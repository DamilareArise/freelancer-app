from django.core.management.base import BaseCommand
from adminHandlers.models import FAQ

class Command(BaseCommand):
    help = "Seed FAQ entries into the database"

    def handle(self, *args, **options):
        data = [
            {"id": 1, "question": "How do I list my property?", "answer": "To list your property, sign in to your account, go to the 'Add Listing' section, fill in the required details, and submit. Our team will review and approve your listing shortly.", "rank": 1},
            {"id": 2, "question": "Are there any fees for listing a property?", "answer": "Basic listings are free. However, we offer premium listing options for better visibility at competitive rates.", "rank": 2},
            {"id": 3, "question": "How can I contact the property owner?", "answer": "Each property listing includes a 'Contact Owner' button. Click it to send a direct inquiry or find the owner's contact details.", "rank": 3},
            {"id": 4, "question": "Is my personal information safe?", "answer": "Yes, we prioritize user privacy. Your contact details are only shared with potential buyers or renters with your consent.", "rank": 4},
            {"id": 5, "question": "Can I edit my property listing after submission?", "answer": "Yes, you can edit your listing anytime from your dashboard. However, major changes may require admin approval.", "rank": 5},
            {"id": 6, "question": "What should I do if I find a fraudulent listing?", "answer": "Please report any suspicious or fraudulent listings using the 'Report' button on the listing page. Our team will investigate immediately.", "rank": 6},
            {"id": 7, "question": "How do I schedule a property visit?", "answer": "You can request a visit by contacting the owner directly through the listing page or using our in-app messaging feature.", "rank": 7},
            {"id": 8, "question": "What documents are required for property verification?", "answer": "Property verification may require ownership documents, tax receipts, and identity proof. Requirements vary based on location.", "rank": 8},
            {"id": 9, "question": "How long does it take for my listing to be approved?", "answer": "Listings are usually reviewed within 24-48 hours. You will be notified once your listing is live.", "rank": 9},
            {"id": 10, "question": "Can I mark my property as sold or rented?", "answer": "Yes, you can update the status of your listing from your dashboard to mark it as sold, rented, or available.", "rank": 10},
            {"id": 11, "question": "How do I increase the visibility of my property listing?", "answer": "You can upgrade to a premium listing, use high-quality images, write a compelling description, and share your listing on social media.", "rank": 11},
            {"id": 12, "question": "What factors affect my property's ranking on the platform?", "answer": "Factors include listing completeness, user engagement, premium listing status, and recent activity on your listing.", "rank": 12},
            {"id": 13, "question": "Can I upload a video tour of my property?", "answer": "Yes! You can add a video link in the media section of your listing to provide potential buyers with a virtual tour.", "rank": 13},
            {"id": 14, "question": "What happens if I receive multiple inquiries for my property?", "answer": "You can respond to each inquiry individually and negotiate with interested buyers or renters to find the best match.", "rank": 14},
            {"id": 15, "question": "How do I update my contact details for a property listing?", "answer": "Go to your account settings or listing dashboard and update your contact information. Changes will reflect on all your active listings.", "rank": 15}
        ]

        for item in data:
            FAQ.objects.update_or_create(
                id=item["id"],
                defaults={
                    "question": item["question"],
                    "answer": item["answer"],
                    "rank": item["rank"],
                },
            )

        self.stdout.write(self.style.SUCCESS("FAQ entries seeded successfully"))
