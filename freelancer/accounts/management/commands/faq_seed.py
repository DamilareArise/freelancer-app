from django.core.management.base import BaseCommand
from adminHandlers.models import FAQ

class Command(BaseCommand):
    help = "Seed FAQ entries into the database"

    def handle(self, *args, **options):
        data = [
            {
                "id": 1,
                "question_en": "How do I list my property?",
                "question_hr": "Kako mogu objaviti svoju nekretninu?",
                "answer_en": "To list your property, sign in to your account, go to the 'Add Listing' section, fill in the required details, and submit. Our team will review and approve your listing shortly.",
                "answer_hr": "Kako biste objavili svoju nekretninu, prijavite se na svoj račun, otvorite odjeljak 'Dodaj oglas', ispunite potrebne podatke i pošaljite zahtjev. Naš tim će uskoro pregledati i odobriti vaš oglas.",
                "rank": 1,
            },
            {
                "id": 2,
                "question_en": "Are there any fees for listing a property?",
                "question_hr": "Postoje li naknade za objavu nekretnine?",
                "answer_en": "Basic listings are free. However, we offer premium listing options for better visibility at competitive rates.",
                "answer_hr": "Osnovna objava nekretnine je besplatna. Međutim, nudimo premium opcije oglasa za bolju vidljivost po konkurentnim cijenama.",
                "rank": 2,
            },
            {
                "id": 3,
                "question_en": "How can I contact the property owner?",
                "question_hr": "Kako mogu kontaktirati vlasnika nekretnine?",
                "answer_en": "Each property listing includes a 'Contact Owner' button. Click it to send a direct inquiry or find the owner's contact details.",
                "answer_hr": "Svaki oglas sadrži gumb 'Kontaktiraj vlasnika'. Kliknite na njega kako biste poslali upit ili pronašli kontakt podatke vlasnika.",
                "rank": 3,
            },
            {
                "id": 4,
                "question_en": "Is my personal information safe?",
                "question_hr": "Jesu li moji osobni podaci sigurni?",
                "answer_en": "Yes, we prioritize user privacy. Your contact details are only shared with potential buyers or renters with your consent.",
                "answer_hr": "Da, privatnost korisnika nam je prioritet. Vaši kontakt podaci dijele se samo s potencijalnim kupcima ili najmoprimcima uz vašu suglasnost.",
                "rank": 4,
            },
            {
                "id": 5,
                "question_en": "Can I edit my property listing after submission?",
                "question_hr": "Mogu li urediti oglas nakon objave?",
                "answer_en": "Yes, you can edit your listing anytime from your dashboard. However, major changes may require admin approval.",
                "answer_hr": "Da, svoj oglas možete urediti u bilo kojem trenutku putem nadzorne ploče. Veće izmjene mogu zahtijevati odobrenje administratora.",
                "rank": 5,
            },
            {
                "id": 6,
                "question_en": "What should I do if I find a fraudulent listing?",
                "question_hr": "Što učiniti ako primijetim lažni oglas?",
                "answer_en": "Please report any suspicious or fraudulent listings using the 'Report' button on the listing page. Our team will investigate immediately.",
                "answer_hr": "Molimo prijavite sumnjive ili lažne oglase pomoću gumba 'Prijavi' na stranici oglasa. Naš tim će odmah provjeriti prijavu.",
                "rank": 6,
            },
            {
                "id": 7,
                "question_en": "How do I schedule a property visit?",
                "question_hr": "Kako mogu dogovoriti razgledavanje nekretnine?",
                "answer_en": "You can request a visit by contacting the owner directly through the listing page or using our in-app messaging feature.",
                "answer_hr": "Razgledavanje možete zatražiti izravnim kontaktom s vlasnikom putem stranice oglasa ili korištenjem poruka unutar aplikacije.",
                "rank": 7,
            },
            {
                "id": 8,
                "question_en": "What documents are required for property verification?",
                "question_hr": "Koji su dokumenti potrebni za provjeru nekretnine?",
                "answer_en": "Property verification may require ownership documents, tax receipts, and identity proof. Requirements vary based on location.",
                "answer_hr": "Provjera nekretnine može zahtijevati vlasničke dokumente, porezne potvrde i dokaz identiteta. Zahtjevi ovise o lokaciji.",
                "rank": 8,
            },
            {
                "id": 9,
                "question_en": "How long does it take for my listing to be approved?",
                "question_hr": "Koliko traje odobrenje oglasa?",
                "answer_en": "Listings are usually reviewed within 24-48 hours. You will be notified once your listing is live.",
                "answer_hr": "Oglasi se obično pregledavaju u roku od 24 do 48 sati. Bit ćete obaviješteni kada vaš oglas postane aktivan.",
                "rank": 9,
            },
            {
                "id": 10,
                "question_en": "Can I mark my property as sold or rented?",
                "question_hr": "Mogu li označiti nekretninu kao prodanu ili iznajmljenu?",
                "answer_en": "Yes, you can update the status of your listing from your dashboard to mark it as sold, rented, or available.",
                "answer_hr": "Da, status oglasa možete promijeniti putem nadzorne ploče i označiti ga kao prodan, iznajmljen ili dostupan.",
                "rank": 10,
            },
        ]

        for item in data:
            FAQ.objects.update_or_create(
                id=item["id"],
                defaults={
                    "question_en": item["question_en"],
                    "question_hr": item["question_hr"],
                    "answer_en": item["answer_en"],
                    "answer_hr": item["answer_hr"],
                    "rank": item["rank"],
                },
            )

        self.stdout.write(self.style.SUCCESS("FAQ entries seeded successfully"))
