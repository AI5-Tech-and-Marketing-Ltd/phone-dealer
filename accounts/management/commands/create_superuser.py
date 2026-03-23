import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser from environment variables if it does not exist'

    def handle(self, *args, **options):
        email = os.getenv('SUPERUSER_EMAIL')
        password = os.getenv('SUPERUSER_PASSWORD')
        full_name = os.getenv('SUPERUSER_FULL_NAME', 'System Admin')

        if not email or not password:
            self.stdout.write(self.style.WARNING('Superuser credentials not found in environment variables.'))
            return

        if not User.objects.filter(email=email).exists():
            # Superusers should always be active regardless of environment
            # but we can respect the production rule if desired. 
            # In this case, we definitely want the seeded superuser to be active.
            user = User.objects.create_superuser(
                email=email,
                password=password,
                full_name=full_name
            )
            # Ensure it is active
            user.is_active = True
            user.is_email_verified = True
            user.save()
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created superuser: {email}'))
        else:
            self.stdout.write(self.style.NOTICE(f'Superuser {email} already exists.'))
