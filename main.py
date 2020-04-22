from autocompletebot import *
while True:
	try:
		run()
	except Exception as e:
		logging.critical(e, exc_info=True)
	logging.info("Sleeping...")
	time.sleep(config.SLEEP_TIME)
				