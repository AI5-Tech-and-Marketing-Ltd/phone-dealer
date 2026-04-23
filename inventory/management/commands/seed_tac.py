import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from inventory.models import TacRecord
from inventory.tac_utils import parse_csv_row, upsert_tac_records

class Command(BaseCommand):
    help = 'Seed TacRecord table from tacdb.csv'

    def add_arguments(self, parser):
        parser.add_argument('--path',       default=None, help='Path to tacdb.csv')
        parser.add_argument('--batch-size', type=int, default=500, help='Batch size for upserts')

    def handle(self, *args, **options):
        path = options['path'] or os.path.join(settings.BASE_DIR, 'tacdb.csv')
        batch_size = options['batch_size']

        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f'File not found: {path}'))
            return

        self.stdout.write(f'Seeding from {path} ...')
        
        with open(path, encoding='utf-8') as f:
            # Skip the first comment line if it exists
            first_line = f.readline()
            if "Osmocom" not in first_line:
                f.seek(0) # Not the comment line, go back to start
            
            reader = csv.reader(f)
            # Skip header if the first row is "tac,name,..."
            first_row = next(reader, None)
            if first_row and first_row[0].lower() != "tac":
                 # It was actually data! (unlikely given our structure but let's be safe)
                 batch = [parse_csv_row(first_row)]
            else:
                 batch = []

            total_created, total_updated = 0, 0
            
            for row in reader:
                r = parse_csv_row(row)
                if r:
                    batch.append(r)
                
                if len(batch) >= batch_size:
                    res = upsert_tac_records(batch)
                    total_created += res['created']
                    total_updated += res['updated']
                    batch = []
                    self.stdout.write(f'Processed {total_created + total_updated} records...')

            if batch:
                res = upsert_tac_records(batch)
                total_created += res['created']
                total_updated += res['updated']

        self.stdout.write(self.style.SUCCESS(
            f'Done. Created: {total_created}, Updated: {total_updated}'
        ))
