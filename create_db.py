from sqlalchemy import create_engine
from app.database import Base, Item, Metadata, Season, Poster

# Create the engine
engine = create_engine('sqlite:///metadata.db')

# Create all tables
Base.metadata.create_all(engine)

print("Database and tables created successfully.")