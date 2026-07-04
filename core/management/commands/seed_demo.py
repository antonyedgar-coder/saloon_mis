from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Deprecated — demo seeding is disabled. Use clear_demo if needed."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "seed_demo is disabled. Demo accounts and particulars are not created."
            )
        )
