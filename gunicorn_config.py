import os

bind = "0.0.0.0:"  + os.getenv("PORT")
workers = 4
threads = 8
timeout = 0