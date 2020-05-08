from acb import MarkovPT, run_model, logging


logging.basicConfig(level=logging.INFO)
logging.basicConfig(filename="log.log", level=logging.INFO,
                    filemode="w")

# model = MarkovPT.get_sando()
# run_model(model, 'all')
model = MarkovPT.get_sando()
run_model(model, 'cremposting')
model = MarkovPT.get_asoiaf()
run_model(model, 'freefolk')
