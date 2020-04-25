from acb import Handler, run_handler, logging, time, config

# # logging.basicConfig(level=logging.INFO)
logging.basicConfig(filename="log.log", level=logging.INFO,
 					filemode="w")

handler = Handler.get_sando_handler()
run_handler(handler, 'cremposting')
handler = Handler.get_asoiaf_handler()
run_handler(handler, 'freefolk')
#handler = Handler.get_star_wars_handler()
#run_handler(handler, 'PrequelMemes')

time.sleep(config.SLEEP_TIME)	