from django.core.management.base import BaseCommand, CommandError
from ingest.pipeline import build_database


class Command(BaseCommand):
    help = "Builds the database from AcousticBrainz dataset dumps."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sample",
            action="store_true",
            help="Use the sample dataset instead of full high-level paths.",
        )
        parser.add_argument(
            "--log",
            action="store_true",
            help="Display parsing errors in console (for debugging)",
        )
        parser.add_argument(
            "--parts",
            type=int,
            default=1,
            help="How many of the 30 AB dumps to use (each folder has 1M records)",
        )

    def handle(self, *args, **options):
        try:
            build_database(
                use_sample=options["sample"],
                show_log=options["log"],
                num_parts=options["parts"],
            )
        except Exception as e:
            raise CommandError(str(e))
        
        self.stdout.write(self.style.SUCCESS("Build complete."))
