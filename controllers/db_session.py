from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os


engine_remote = create_engine(os.environ['BLUBASE_DATABASE_URL'])
DBSession_remote = sessionmaker(bind=engine_remote)
session_remote = DBSession_remote()

engine_heroku = create_engine(os.environ['DATABASE_URL'])
DBSession_heroku = sessionmaker(bind=engine_heroku)
session_heroku = DBSession_heroku()
