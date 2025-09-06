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
            default=None,
            help="How many of the 30 AB dumps to use (each folder has 1M records)",
        )
        parser.add_argument(
            "--parts_list",
            type=str,
            default=None,
            help="List of part indexes to process (optional).",
        )

    def handle(self, *args, **options):
        try:
            parts_list = options.get("parts_list", None)
            if parts_list:
                parts_list = [int(part) for part in options["parts_list"].split(",")]

            build_database(
                use_sample=options["sample"],
                show_log=options["log"],
                num_parts=options["parts"],
                parts_list=parts_list
            )
        except Exception as e:
            raise CommandError(str(e))
        
        self.stdout.write(self.style.SUCCESS("Build complete."))
