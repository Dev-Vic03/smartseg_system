import sys
import traceback
from sqlalchemy.engine import create_engine
try:
    create_engine("mysql-123.aivencloud.com:12345/defaultdb")
except Exception as e:
    traceback.print_exc()
