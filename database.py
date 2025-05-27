import os
from databases import Database
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = "postgresql://postgres.ehnguyuzpffqzaednrnn:z8O26qYv4Perh997@aws-0-eu-west-2.pooler.supabase.com:6543/postgres"
database = Database(DATABASE_URL)