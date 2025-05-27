import os
import databases
import sqlalchemy

DATABASE_URL = os.getenv("DATABASE_URL")  # или впиши напрямую

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

cbt_cards = sqlalchemy.Table(
    "cbt_cards",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.dialects.postgresql.UUID, primary_key=True),
    sqlalchemy.Column("user_id", sqlalchemy.dialects.postgresql.UUID),
    sqlalchemy.Column("situation", sqlalchemy.Text),
    sqlalchemy.Column("thoughts", sqlalchemy.Text),
    sqlalchemy.Column("emotions", sqlalchemy.Text),
    sqlalchemy.Column("intensity", sqlalchemy.Integer),
)

engine = sqlalchemy.create_engine(DATABASE_URL)
metadata.create_all(engine)