import markovify, re, json, praw, datetime, time, sqlite3
import reddit_config as config
import logging 
logging.basicConfig(level=logging.INFO)







	
#####################################################################################################################
#####################################################################################################################
logging.info("Loading natural language library...")

import nltk
class POSifiedText(markovify.Text):
    def word_split(self, sentence):
        words = re.split(self.word_split_pattern, sentence)
        words = [ "::".join(tag) for tag in nltk.pos_tag(words) ]
        return words

    def word_join(self, words):
        sentence = " ".join(word.split("::")[0] for word in words)
        return sentence



def save_model_as_json(text_model, file_name):
	model_json = text_model.to_json()
	with open(file_name, 'w') as outfile:
		json.dump(model_json, outfile)
		
def load_model_from_json(file_name,pos = False):
	with open(file_name) as json_file:
		if pos:
			return POSifiedText.from_json(json.load(json_file))		
		
def create_models_and_save(sample_file, output_name, pos = False):
	with open(sample_file, 'r', encoding = "utf-8") as file:
		if pos:
			type_of_model = 'pos.txt'
			model = POSifiedText(file, state_size = 1)
			save_model_as_json(model, output_name + " 1 " + type_of_model)
			model = POSifiedText(file, state_size = 2)
			save_model_as_json(model, output_name + " 2 " + type_of_model)
			model = POSifiedText(file, state_size = 3)
			save_model_as_json(model, output_name + " 3 " + type_of_model)
		else:
			type_of_model = 'mark.txt'
			model = markovify.Text(file, state_size = 1)
			save_model_as_json(model, output_name + " 1 " + type_of_model)
			model = markovify.Text(file, state_size = 2)
			save_model_as_json(model, output_name + " 2 " + type_of_model)
			model = markovify.Text(file, state_size = 3)
			save_model_as_json(model, output_name + " 3 " + type_of_model)
	
		
		



		

	
logging.info("Setting up models...")
# three_word_model = load_model_from_json('model brando 3 word.txt')
# two_word_model = load_model_from_json('model brando 2 word.txt')
# one_word_model = load_model_from_json('model brando 1 word.txt')
	
	

three_word_model = load_model_from_json('brando 3 pos.txt', True)
two_word_model = load_model_from_json('brando 2 pos.txt', True)
one_word_model = load_model_from_json('brando 1 pos.txt', True)

with open('brando 2 pos.txt') as json_file:
	two_word_model = POSifiedText.from_json(json.load(json_file))
	
with open('brando 1 pos.txt') as json_file:
	one_word_model =POSifiedText.from_json(json.load(json_file))
	
logging.info("Setup complete.")

#####################################################################################################################


######################################################################################################################		
#the database of comments that have been completed
#"CREATE TABLE comments (id INTEGER PRIMARY KEY, comment_id TEXT, user TEXT, body TEXT, completion TEXT, date INTEGER)"
#database of user
#"CREATE TABLE banned (id INTEGER PRIMARY KEY, user TEXT)"
#table of comments the bot couldn't complete (for debbuging)
#"CREATE TABLE failures (id INTEGER PRIMARY KEY, body TEXT)"
#database of all comments replied
######################################################################################################################
class Database:
	def __init__(self, database = config.database):
		self.database = database
		self.connection = sqlite3.connect(database)
		self.cursor = self.connection.cursor()
		
	def open_database(self, database = config.database):
		self.connection = sqlite3.connect(database)
		self.cursor = self.connection.cursor()
		return self.connection, self.cursor
	
	def show_content(self):
		print("This is the content of the database:")
		matches = self.cursor.execute("SELECT * FROM comments ORDER BY id").fetchall()
		for row in matches:
			print(row)
	
	def show_completions(self):
		print("\n-------------------------------------------------------\n"
			"Those are the completions in the database:")
		matches = self.cursor.execute("SELECT body, completion FROM comments ORDER BY id").fetchall()
		for row in matches:
			print("-------------------------------------------------------")
			if len(row[0]) > 50:
				print("[...]" + row[0][-30:])
			else:
				print(row[0])
			print(row[1])
			
	def get_size(self):
		size = self.cursor.execute("SELECT COUNT(*) FROM comments").fetchall()[0][0]
		return size
			
	def delete_entire_database(self):
		print("Are you sure? (y/n)")
		confirmation = input()
		if confirmation =="y":
			self.cursor.execute("DELETE FROM comments")
			self.connection.commit()
	
	def check_replied(self, comment):
		matches = self.cursor.execute("SELECT COUNT(*) FROM comments "
					"WHERE comment_id = '%s' LIMIT 1"%comment.fullname).fetchall()[0][0]
		if matches > 0:
			return True
		return False
	
	def adapt_datetime(self,ts):
		return int(time.mktime(ts.timetuple()))
	
	def add_to(self, comment, completion):
		logging.info("Adding comment to database...")
		self.cursor.execute("INSERT INTO comments (comment_id, user, body, completion, date) "\
			"VALUES (?, ?, ?, ?, ?)", (comment.fullname, comment.author.name, comment.body,
			completion, self.adapt_datetime(datetime.date.today())))
		self.connection.commit()
		logging.info("Comment added!!!!!!!!")
		
	def ban_author(self, author):
		logging.info("Banned %s"%(author.name))
		self.cursor.execute("INSERT INTO banned (user) VALUES (?)", (author.name,))
		self.connection.commit()
		
	def show_banned(self):
		matches = self.cursor.execute("SELECT * FROM banned ORDER BY id").fetchall()
		for row in matches:
			print(row)
	
	def check_banned(self, author):
		matches = self.cursor.execute("SELECT COUNT(*) FROM banned "
					"WHERE user = ? LIMIT 1",(author.name,)).fetchall()[0][0]
		if matches > 0:
			return True
		return False
		
	def close_database(self):
		self.connection.commit()
		self.connection.close()
		
	def add_failure(self, comment):
		logging.info("Adding comment to failures...")
		self.cursor.execute("INSERT INTO failures (body) "\
			"VALUES (?)", (comment.body,))
		self.connection.commit()
		logging.info("Comment added to failures.")
		
	def show_failures(self):
		print("\n-------------------------------------------------------\n"
			"Those are the failures in the database:")
		matches = self.cursor.execute("SELECT * FROM failures ORDER BY id").fetchall()
		for row in matches:
			print("-------------------------------------------------------")
			if len(row[1]) > 30:
				print("[...]" + row[1][-30:])
			else:
				print(row[1])
			
	def delete_failures(self):
		print("Are you sure? (y/n)")
		confirmation = input()
		if confirmation =="y":
			self.cursor.execute("DELETE FROM failures")
			self.connection.commit()
	
		
	


#########################################################################################
#########################################################################################
#########################################################################################
#the first one matches only phrases with only one word.
#the second one matches the last two words in a phrase with two words
one_word_pattern = re.compile(r'^(\w*)\.*$')
two_word_pattern = re.compile(r'(.*\s|\A)(\S*\s\w*)\.*$')
three_word_pattern = re.compile(r'(.*\s|\A)(\S*\s\S*\s\w*)\.*$')
#return the last words and the ammount of words it could extract.
#tries to extract the most amount of words at the end.
def get_last_words(sentence):
	logging.debug("Extracting ending of sentence \"{}\"".format(sentence))
	try:
		words = re.findall(three_word_pattern, sentence)[0][1]
		return words, 3
	except:
		logging.debug("Could not return three words")
		try:
			words = re.findall(two_word_pattern, sentence)[0][1]
			return words, 2
		except:
			logging.debug("Could not return two words")
			try:
				words = re.findall(one_word_pattern, sentence)[0]
				return words,1
			except:
				logging.debug("Could not return one word")
				return None, 0

		
#formats the completion the way we want it
def remove_fist_words(word, amount):
	return ' '.join(word.split(' ')[amount:])


def complete_with_model(ending, model, amount):
		completion = None
		try:
			while completion == None:
				logging.debug("We have this value for the ending: %s"%ending)
				completion = model.make_sentence_with_start(ending)
				
			if len(completion) < config.IDEAL_LEN:
				completion += " " + model.make_sentence()
			logging.debug("We obtained the completion %s"%completion)
			return "..." +remove_fist_words(completion, amount)
		except:
			return None
			
			
#This return a completion if the model can handle the sentence and None if not
def complete_sentence(sentence):
	ending, amount = get_last_words(sentence)
	logging.debug("Ending:{}\nAmount:{}".format(ending, amount))
	
	if amount == 3:
		completion = complete_with_model(ending, three_word_model, 3)
		if completion != None:
			return completion
		amount = 2
		ending = remove_fist_words(ending, 1)
	if amount == 2:
		completion = complete_with_model(ending, two_word_model, 2)
		logging.debug("We achieved the following completion on 2 words:\n{}".format(\
						completion))
		if completion != None:
			return completion
		amount = 1
		ending = remove_fist_words(ending, 1)
	elif amount == 1:
		completion = complete_with_model(ending, one_word_model, 1)
		logging.debug("We achieved the following completion on 1 word:\n{}".format(\
						completion))
		if completion != None:
			return completion
	return None
			


#########################################################################################
#########################################################################################
#########################################################################################
				
	
def login():
	logging.info("Logging in...")
	r = praw.Reddit(username = config.user, 
				password = config.password,
				client_id = config.client_id,
				client_secret = config.client_secret,
				user_agent = "sandocomplete")
	logging.info("Logged!")
	return r
	
def check_inbox(reddit, database):
	for reply in reddit.inbox.comment_replies():
		if config.SAFE_WORD in reply.body and not database.check_banned(reply.author):
			logging.info(reply.author)
			reply.reply("*The bot commits sepuku.*")
			database.ban_author(reply.author)
			#logging.info("%s is banned!"%reply.author.name)
			
def reply_completion(comment, completion):
	message = " {}\n\n {}\n\n {} {}".format(completion,
		"-------------------------------------------------------",
		"^^I ^^am ^^a ^^bot, ^^this ^^reply ^^was ^^perfomed ^^automatically.",
		"^^Reply ^^!NOMORE ^^if ^^you ^^would ^^like ^^me ^^to ^^stop ^^replying ^^to ^^your ^^comments.")
	comment.reply(message)
	
def delete_bad_comments(reddit):
	user_comments = reddit.user.me().comments.new(limit=10)
	for comment in user_comments:
		if comment.score < 1:
			logging.info("Deleted a comment.")
			comment.delete()

			
	
def run():
	replied_comments = []
	database = Database()
	reddit = login()
	
	logging.info("Checking inbox.")
	check_inbox(reddit,database)
	
	logging.info("Deleting bad replies.")
	delete_bad_comments(reddit)
	
	logging.info("Opening sub...")
	sub = reddit.subreddit(config.SUB_NAME)
	logging.info("Sub opened!")
	logging.info("Getting posts...")
	hot_submissions = sub.hot(limit = config.NUM_OF_POSTS)
	
	
	for post in hot_submissions:
		logging.info("-------------------------------------------------------\n"+
					post.url)
		if post.archived:
				logging.info("Post was archived")
				continue
		
		#without this the code breaks when reading a 'more comments'
		post.comments.replace_more(limit=0)
		all_comments = post.comments.list()
		
		for comment in all_comments:
			if not comment.author:
				logging.info("Couldn't find author.")
				continue
			if database.check_banned(comment.author):
				logging.info("Author is banned")
				continue
			if comment.body[len(comment.body) - 3:] == "...":
				if database.check_replied(comment):
					logging.info("Already replied to comment")
					continue #skips this if it has already replied to comment
				logging.info("Found matching comment!")
				logging.info(comment.body[-50:])
				
				completion = complete_sentence(comment.body)
				logging.info('Completion: %s'%completion)
				if completion != None and "::" not in completion:
					#reply_completion(comment, completion)
					#database.add_to(comment, completion)
					replied_comments.append([post.url,comment.body[-50:],completion])
				else:
					#database.add_failure(comment)
					pass
	#database.show_completions()
	#database.show_failures()
	logging.info("-------------------------------------------------------\nThe replies in this run:")
	for comment in replied_comments:
		logging.info("-------------------------------------------------------\n{}"\
			"\n{}\n{}".format(comment[0], comment[1], comment[2]))
			
	logging.info("-------------------------------------------------------\n" +
		"In this run we added %s comments to the database.\n"%len(replied_comments) +
		"The database has a total of %s comments."%database.get_size())
		
	database.connection.close()

				

				

				
# endings = ["This is turning...","What is...", "to focus..."]
# for sentence in endings:
	# print("-----------------------------------------------------------")
	# for i in range (5):
		# try:
			# completion = None
			# while completion == None:
				# completion = complete_sentence(sentence)
				# print(completion)
				# time.sleep(1)
			# print(completion)
				
		# except Exception as e:
			# logging.critical(e, exc_info=True)
				


				
				
				
				
				
				
				
				
				
				