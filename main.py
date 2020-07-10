from src.bot import run_on_a_sub, logging, delete_bad_comments
import config

logging.basicConfig(level=logging.INFO)
logging.basicConfig(filename="log.log", level=logging.INFO,
                    filemode="w")
print("OK")
delete_bad_comments()
subs = config.SUBNAMES
for sub in subs():
    run_on_a_sub(sub)
